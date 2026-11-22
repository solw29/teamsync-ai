"""DB jobs+outbox are durable authority; Celery messages contain only job IDs."""

import hashlib
import random
import time
from datetime import timedelta

from kombu.exceptions import KombuError
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .errors import DomainError, SyncError
from .models import Audit, Job, JobEvent, Outbox, Repository, SyncCursor, now, uid
from .storage import save_v2
from .telemetry import record


def enqueue(db, repo, run_id, attempt, key, request_id=None):
    hashed = hashlib.sha256(f"{repo.id}:{run_id}:{attempt}:{key}".encode()).hexdigest()
    existing = db.scalar(select(Job).where(Job.idempotency_key == hashed))
    if existing:
        return existing
    try:
        with db.begin_nested():
            job = Job(
                request_id=request_id,
                repository_id=repo.id,
                run_id=run_id,
                run_attempt=attempt,
                idempotency_key=hashed,
            )
            db.add(job)
            db.flush()
            db.add(Outbox(job_id=job.id, seq=0))
            db.add(JobEvent(job_id=job.id, status="queued"))
            db.add(
                Audit(
                    actor_id=repo.owner_id, action="resync_requested", target_id=job.id
                )
            )
            db.flush()
    except IntegrityError:
        job = db.scalar(select(Job).where(Job.idempotency_key == hashed))
        if not job:
            raise DomainError("job_conflict", 409) from None
    return job


def dispatch(factory, send, settings, limit=20, after_send=None):
    delivered = 0
    with factory.begin() as db:
        pending = db.scalars(
            select(Outbox)
            .where(Outbox.sent_at.is_(None), Outbox.available_at <= now())
            .order_by(Outbox.available_at, Outbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for entry in pending:
            job = db.get(Job, entry.job_id)
            if not job or job.status in ("succeeded", "failed", "cancelled"):
                entry.sent_at = now()
                continue
            try:
                send(entry.job_id)
            except (OSError, KombuError):
                entry.send_attempts += 1
                entry.available_at = now() + timedelta(
                    seconds=min(
                        60, settings.retry_base * 2 ** min(entry.send_attempts, 6)
                    )
                )
                if entry.send_attempts >= settings.max_attempts:
                    job.status, job.reason, job.finished_at = (
                        "failed",
                        "broker_unavailable",
                        now(),
                    )
                    db.add(JobEvent(job_id=job.id, status="failed", reason=job.reason))
                continue
            if after_send:
                after_send(
                    entry.job_id
                )  # Fault injection: transaction rollback -> duplicate send is safe.
            entry.sent_at = now()
            delivered += 1
    return delivered


def claim(factory, job_id, settings):
    with factory.begin() as db:
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if (
            not job
            or job.status not in ("queued", "retrying")
            or (
                job.next_retry_at
                and job.next_retry_at.replace(tzinfo=now().tzinfo) > now()
            )
        ):
            return None
        job.status, job.lease_token = "running", uid()
        job.attempts += 1
        job.lease_until, job.updated_at = (
            now() + timedelta(seconds=settings.lease_seconds),
            now(),
        )
        db.add(JobEvent(job_id=job.id, status="running"))
        token = job.lease_token
        details = {
            "jobId": job.id,
            "runId": job.run_id,
            "requestId": job.request_id,
            "attempt": job.attempts,
            "queueWaitMs": round(
                (now() - job.created_at.replace(tzinfo=now().tzinfo)).total_seconds()
                * 1000,
                2,
            ),
        }
    record("job_started", **details)
    return token


def fail(factory, job_id, token, error, settings):
    with factory.begin() as db:
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if not job or job.lease_token != token or job.status != "running":
            return
        job.reason, job.updated_at, job.lease_until = error.code, now(), None
        if error.retryable and job.attempts < settings.max_attempts:
            delay = (
                error.retry_after
                if error.retry_after is not None
                else settings.retry_base * 2 ** (job.attempts - 1) + random.random()
            )
            job.next_retry_at, job.status = now() + timedelta(seconds=delay), "retrying"
            job.delivery_seq += 1
            db.add(
                Outbox(
                    job_id=job.id, seq=job.delivery_seq, available_at=job.next_retry_at
                )
            )
        else:
            job.status, job.finished_at = "failed", now()
        db.add(JobEvent(job_id=job.id, status=job.status, reason=job.reason))
        cursor = db.get(SyncCursor, job.repository_id)
        if cursor:
            cursor.last_error = error.code


def process(factory, job_id, settings, connector_factory, cache=None):
    token = claim(factory, job_id, settings)
    if not token:
        return "duplicate_or_busy"
    connector = None
    started = time.monotonic()
    try:
        with factory() as db:
            job = db.get(Job, job_id)
            repo = db.get(Repository, job.repository_id)
            if not repo or not repo.enabled:
                raise SyncError("repository_disabled")
            # Detached values are immutable inputs for the external fetch.
            repo_id, old_version = repo.id, repo.stats_version
            connector = connector_factory()
            report, github, canonical_name = connector.sync(
                repo, job.run_id, job.run_attempt
            )
        with factory.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.lease_token != token or job.status != "running":
                return "stale_worker"
            repo = db.get(Repository, repo_id)
            if not repo.enabled:
                raise SyncError("repository_disabled")
            repo.full_name = canonical_name
            save_v2(db, repo, report, github)
            job.status, job.updated_at, job.finished_at = "succeeded", now(), now()
            job.lease_until, job.reason = None, None
            db.add(JobEvent(job_id=job.id, status="succeeded"))
            cursor = db.get(SyncCursor, repo.id)
            if not cursor:
                cursor = SyncCursor(repository_id=repo.id)
                db.add(cursor)
            cursor.last_synced_at, cursor.last_error = now(), None
            db.add(
                Audit(
                    actor_id=repo.owner_id,
                    action="report_collected",
                    target_id=str(report.identity.runId),
                )
            )
        if cache:
            with factory() as db:
                cache.invalidate(db.get(Repository, repo_id), old_version)
        record(
            "job_succeeded",
            jobId=job_id,
            durationMs=round((time.monotonic() - started) * 1000, 2),
        )
        return "succeeded"
    except SyncError as error:
        fail(factory, job_id, token, error, settings)
        record("job_attempt_failed", jobId=job_id, reason=error.code)
        return "retrying_or_failed"
    except DomainError as error:
        fail(factory, job_id, token, SyncError(error.code), settings)
        return "failed"
    except (OSError, ValueError, SQLAlchemyError):
        fail(
            factory,
            job_id,
            token,
            SyncError("storage_or_internal_unavailable", True),
            settings,
        )
        return "retrying_or_failed"
    finally:
        if connector:
            connector.close()


def reconcile(factory, settings):
    recovered = 0
    with factory.begin() as db:
        stale = db.scalars(
            select(Job)
            .where(
                or_(
                    and_(Job.status == "running", Job.lease_until < now()),
                    and_(
                        Job.status.in_(["queued", "retrying"]),
                        Job.updated_at
                        < now() - timedelta(seconds=settings.lease_seconds),
                    ),
                )
            )
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            pending = db.scalar(
                select(Outbox.id).where(
                    Outbox.job_id == job.id, Outbox.sent_at.is_(None)
                )
            )
            if job.status != "running" and pending:
                continue
            job.lease_token, job.lease_until, job.updated_at = None, None, now()
            if job.attempts >= settings.max_attempts:
                job.status, job.reason, job.finished_at = (
                    "failed",
                    "worker_lease_exhausted",
                    now(),
                )
            else:
                job.status, job.reason, job.next_retry_at = (
                    "retrying",
                    "worker_lease_expired",
                    now(),
                )
                job.delivery_seq += 1
                db.add(Outbox(job_id=job.id, seq=job.delivery_seq, available_at=now()))
            db.add(JobEvent(job_id=job.id, status=job.status, reason=job.reason))
            recovered += 1
    return recovered


def discover(factory, client, settings):
    """Overlap cursor; only source-owned workflow results are candidates."""
    with factory() as db:
        repos = db.scalars(select(Repository).where(Repository.enabled)).all()
    for detached in repos:
        try:
            info = client.repository(detached)
            with factory.begin() as db:
                repo = db.get(Repository, detached.id)
                cursor = db.get(SyncCursor, repo.id)
                start = (
                    cursor.last_scan_at - timedelta(minutes=10)
                    if cursor and cursor.last_scan_at
                    else now() - timedelta(days=1)
                )
                for workflow in repo.workflow_ids:
                    for page in range(1, 4):
                        runs = client.get(
                            f"/repos/{info['full_name']}/actions/workflows/{workflow}/runs",
                            {
                                "per_page": 100,
                                "page": page,
                                "created": ">=" + start.isoformat(),
                            },
                        ).get("workflow_runs", [])
                        for run in runs:
                            if (
                                run.get("event") != "pull_request"
                                or run.get("status") != "completed"
                            ):
                                continue
                            enqueue(
                                db,
                                repo,
                                run["id"],
                                run["run_attempt"],
                                f"discover:{run['id']}:{run['run_attempt']}:{run['updated_at']}",
                            )
                        if len(runs) < 100:
                            break
                    else:
                        raise SyncError("sync_page_limit")
                if not cursor:
                    cursor = SyncCursor(repository_id=repo.id)
                    db.add(cursor)
                cursor.last_scan_at, cursor.last_error = now(), None
        except SyncError as error:
            with factory.begin() as db:
                cursor = db.get(SyncCursor, detached.id)
                if not cursor:
                    cursor = SyncCursor(repository_id=detached.id)
                    db.add(cursor)
                cursor.last_error = error.code

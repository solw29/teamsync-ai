import base64
import hashlib
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import redis
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache import StatsCache
from .config import Settings
from .db import database
from .errors import DomainError
from .jobs import enqueue
from .models import (
    Audit,
    Installation,
    Job,
    JobEvent,
    PullRequest,
    Repository,
    Run,
    SyncCursor,
    now,
)
from .schemas import (
    DetailResponse,
    ErrorResponse,
    JobResponse,
    RepositoriesResponse,
    RunsResponse,
    SessionResponse,
    StatsResponse,
)
from .security import authenticate, bootstrap, digest, login
from .storage import import_v1, iso, owned_repository


class Credentials(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{3,64}$")
    password: SecretStr = Field(min_length=12, max_length=128)


class Bootstrap(Credentials):
    token: SecretStr


class RepositoryInput(BaseModel):
    externalId: int = Field(gt=0)
    fullName: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    workflowIds: list[int] = Field(min_length=1, max_length=10)


class SyncInput(BaseModel):
    runId: int = Field(gt=0)
    runAttempt: int = Field(gt=0)


def create_app(settings=None, engine=None, factory=None, cache=None):
    settings = settings or Settings.from_env()
    if factory is None:
        engine, factory = database(settings.database_url)
    app = FastAPI(
        title="TeamSync results API",
        version="0.3.0",
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 401, 403, 404, 409, 413, 422, 429, 503)
        },
    )
    app.state.settings, app.state.engine, app.state.factory = settings, engine, factory
    app.state.cache = cache or StatsCache(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    )
    failures = {}

    @app.middleware("http")
    async def boundaries(request, call_next):
        request.state.request_id = str(uuid.uuid4())
        started = time.monotonic()
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            if origin and origin not in settings.origins:
                return JSONResponse(
                    {
                        "error": {
                            "code": "origin_rejected",
                            "requestId": request.state.request_id,
                        }
                    },
                    status_code=403,
                )
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > 5_000_000:
                return JSONResponse(
                    {
                        "error": {
                            "code": "request_size_limit",
                            "requestId": request.state.request_id,
                        }
                    },
                    status_code=413,
                )
            chunks = []
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 5_000_000:
                    return JSONResponse(
                        {
                            "error": {
                                "code": "request_size_limit",
                                "requestId": request.state.request_id,
                            }
                        },
                        status_code=413,
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
        result = await call_next(request)
        result.headers["X-Request-ID"] = request.state.request_id
        result.headers["Cache-Control"] = "no-store"
        # Only correlation/status/timing. Never log URL query/body/credentials.
        print(
            json.dumps(
                {
                    "event": "request",
                    "requestId": request.state.request_id,
                    "status": result.status_code,
                    "durationMs": round((time.monotonic() - started) * 1000, 2),
                }
            ),
            flush=True,
        )
        return result

    @app.exception_handler(DomainError)
    async def domain(request, error):
        return JSONResponse(
            {"error": {"code": error.code, "requestId": request.state.request_id}},
            status_code=error.status,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "requestId": request.state.request_id,
                }
            },
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        return JSONResponse(
            {
                "error": {
                    "code": "route_not_found"
                    if error.status_code == 404
                    else "request_rejected",
                    "requestId": request.state.request_id,
                }
            },
            status_code=error.status_code,
        )

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request, error):
        return JSONResponse(
            {
                "error": {
                    "code": "database_unavailable",
                    "requestId": request.state.request_id,
                }
            },
            status_code=503,
        )

    def db_session():
        with factory() as db:
            yield db

    db_dependency = Depends(db_session)

    def access(request: Request, db=db_dependency):
        session, user = authenticate(db, request.cookies.get("teamsync_session", ""))
        return db, session, user

    access_dependency = Depends(access)

    def write_access(request: Request, context=access_dependency):
        _db, session, _user = context
        provided = request.headers.get("x-csrf-token", "")
        if not provided or not secrets.compare_digest(
            digest(provided), session.csrf_hash
        ):
            raise DomainError("csrf_required", 403)
        return context

    write_dependency = Depends(write_access)

    @app.get("/health")
    def health():
        return {"status": "alive"}

    @app.get("/ready")
    def ready(db=db_dependency):
        db.execute(text("SELECT 1"))
        return {"status": "ready"}

    @app.get("/api/auth/setup-status")
    def setup_status(db=db_dependency):
        return {"initialized": bool(db.get(Installation, 1))}

    @app.post("/api/auth/bootstrap", status_code=201)
    def setup(body: Bootstrap, db=db_dependency):
        try:
            bootstrap(
                db,
                settings,
                body.token.get_secret_value(),
                body.username,
                body.password.get_secret_value(),
            )
            db.add(Audit(action="administrator_initialized", target_id="installation"))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise DomainError("already_initialized", 409) from None
        return {"initialized": True}

    @app.post("/api/auth/login", response_model=SessionResponse)
    def signin(
        body: Credentials, request: Request, response: Response, db=db_dependency
    ):
        address = request.client.host if request.client else "local"
        history = [t for t in failures.get(address, []) if time.monotonic() - t < 60]
        if len(history) >= 6:
            raise DomainError("login_rate_limited", 429)
        try:
            token, csrf, user = login(
                db,
                body.username,
                body.password.get_secret_value(),
                settings.session_seconds,
            )
        except DomainError:
            failures[address] = history + [time.monotonic()]
            raise
        db.commit()
        failures.pop(address, None)
        response.set_cookie(
            "teamsync_session",
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.session_seconds,
            path="/",
        )
        return {"username": user.username, "csrfToken": csrf}

    @app.get("/api/auth/me", response_model=SessionResponse)
    def me(context=access_dependency):
        db, session, user = context
        # Rotate CSRF without exposing or recovering a stored secret.
        csrf = secrets.token_urlsafe(32)
        session.csrf_hash = digest(csrf)
        db.commit()
        return {"username": user.username, "csrfToken": csrf}

    @app.post("/api/auth/logout")
    def logout(response: Response, context=write_dependency):
        db, session, _ = context
        db.delete(session)
        db.commit()
        response.delete_cookie("teamsync_session", path="/")
        return {"loggedOut": True}

    @app.get("/api/repositories", response_model=RepositoriesResponse)
    def repositories(context=access_dependency):
        db, _, user = context
        return {
            "items": [
                {
                    "id": r.id,
                    "externalId": r.external_id,
                    "fullName": r.full_name,
                    "workflowIds": r.workflow_ids,
                }
                for r in db.scalars(
                    select(Repository).where(
                        Repository.owner_id == user.id, Repository.enabled
                    )
                )
            ]
        }

    @app.post("/api/repositories", status_code=201)
    def add_repository(body: RepositoryInput, context=write_dependency):
        db, _, user = context
        if not all(x > 0 for x in body.workflowIds):
            raise DomainError("invalid_workflow_id")
        repo = Repository(
            external_id=body.externalId,
            owner_id=user.id,
            full_name=body.fullName,
            workflow_ids=body.workflowIds,
        )
        db.add(repo)
        try:
            db.flush()
            db.add(SyncCursor(repository_id=repo.id))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise DomainError("repository_already_connected", 409) from None
        return {"id": repo.id, "fullName": repo.full_name}

    def run_access(db, user, run_id):
        run = db.get(Run, run_id)
        if not run:
            raise DomainError("run_not_found", 404)
        repo = owned_repository(db, run.repository_id, user.id)
        return run, repo

    @app.get("/api/runs", response_model=RunsResponse)
    def list_runs(
        repositoryId: str,
        q: str = Query("", max_length=200),
        status: str = Query("all", pattern=r"^(all|passed|failed|running|partial)$"),
        start: datetime | None = None,
        end: datetime | None = None,
        sort: Literal["new", "old", "reviews"] = "new",
        cursor: str | None = Query(None, max_length=2000),
        limit: int = Query(20, ge=1, le=100),
        context=access_dependency,
    ):
        db, _, user = context
        repo = owned_repository(db, repositoryId, user.id)
        fingerprint = hashlib.sha256(
            json.dumps(
                [
                    repo.id,
                    q,
                    status,
                    sort,
                    start.isoformat() if start else None,
                    end.isoformat() if end else None,
                ]
            ).encode()
        ).hexdigest()[:16]
        stmt = select(Run).where(Run.repository_id == repo.id)
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=now().tzinfo)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=now().tzinfo)
        if start and end and start > end:
            raise DomainError("invalid_period")
        if start:
            stmt = stmt.where(Run.github_created_at >= start)
        if end:
            stmt = stmt.where(Run.github_created_at <= end)
        if status != "all":
            stmt = stmt.where(Run.analysis_status == status)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                or_(
                    Run.ui["prTitle"]
                    .as_string()
                    .ilike("%" + escaped + "%", escape="\\"),
                    Run.ui["repository"]
                    .as_string()
                    .ilike("%" + escaped + "%", escape="\\"),
                    Run.pull_request_id.in_(
                        select(PullRequest.id).where(PullRequest.number == int(q))
                    )
                    if q.isdigit() and len(q) <= 9
                    else False,
                )
            )
        if cursor:
            try:
                data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if (
                    data["f"] != fingerprint
                    or not isinstance(data.get("n"), int)
                    or data["n"] < 0
                ):
                    raise ValueError()
                timestamp = datetime.fromisoformat(data["t"])
                identifier = str(uuid.UUID(data["id"]))
                tie = or_(
                    Run.created_at < timestamp,
                    and_(Run.created_at == timestamp, Run.id < identifier),
                )
                if sort == "old":
                    tie = or_(
                        Run.created_at > timestamp,
                        and_(Run.created_at == timestamp, Run.id > identifier),
                    )
                if sort == "reviews":
                    tie = or_(
                        Run.finding_count < data["n"],
                        and_(Run.finding_count == data["n"], tie),
                    )
                stmt = stmt.where(tie)
            except (ValueError, KeyError, TypeError):
                raise DomainError("invalid_cursor") from None
        order = (
            [Run.created_at.asc(), Run.id.asc()]
            if sort == "old"
            else [Run.created_at.desc(), Run.id.desc()]
        )
        if sort == "reviews":
            order.insert(0, Run.finding_count.desc())
        rows = list(db.scalars(stmt.order_by(*order).limit(limit + 1)))
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "f": fingerprint,
                        "t": last.created_at.isoformat(),
                        "id": last.id,
                        "n": last.finding_count,
                    }
                ).encode()
            ).decode()
        sync = db.get(SyncCursor, repo.id)
        return {
            "items": [r.ui for r in rows[:limit]],
            "nextCursor": next_cursor,
            "source": "api",
            "lastSyncedAt": iso(sync.last_synced_at) if sync else None,
            "syncError": sync.last_error if sync else None,
        }

    @app.get("/api/runs/{run_id}", response_model=DetailResponse)
    def detail(run_id: str, context=access_dependency):
        db, _, user = context
        run, _ = run_access(db, user, run_id)
        return {
            "analysis": run.ui,
            "schemaVersion": run.schema_version,
            "runAttempt": run.attempt or None,
            "githubStatus": run.github_status,
            "githubConclusion": run.github_conclusion,
            "collectionStatus": run.collection_status,
            "collectedAt": iso(run.collected_at),
        }

    @app.get("/api/repositories/{repo_id}/pulls/{number}/history")
    def history(repo_id: str, number: int, context=access_dependency):
        db, _, user = context
        repo = owned_repository(db, repo_id, user.id)
        rows = list(
            db.scalars(
                select(Run)
                .join(PullRequest, PullRequest.id == Run.pull_request_id)
                .where(Run.repository_id == repo.id, PullRequest.number == number)
                .order_by(
                    Run.github_created_at.desc(), Run.attempt.desc(), Run.id.desc()
                )
                .limit(100)
            )
        )
        success = next((r for r in rows if r.analysis_status == "passed"), None)
        return {
            "items": [
                {
                    "id": r.id,
                    "runId": r.github_run_id,
                    "attempt": r.attempt or None,
                    "status": r.analysis_status,
                }
                for r in rows
            ],
            "latest": rows[0].id if rows else None,
            "latestSuccessful": success.id if success else None,
        }

    @app.get("/api/repositories/{repo_id}/stats", response_model=StatsResponse)
    def stats(
        repo_id: str, days: int = Query(30, ge=1, le=365), context=access_dependency
    ):
        db, _, user = context
        repo = owned_repository(db, repo_id, user.id)
        return app.state.cache.stats(db, repo, days)

    @app.post("/api/repositories/{repo_id}/import")
    async def legacy(repo_id: str, request: Request, context=write_dependency):
        db, _, user = context
        repo = owned_repository(db, repo_id, user.id)
        old = repo.stats_version
        try:
            raw = await request.json()
            count = import_v1(db, repo, raw)
            db.commit()
        except (ValueError, KeyError, TypeError):
            db.rollback()
            raise DomainError("invalid_report") from None
        app.state.cache.invalidate(repo, old)
        return {"created": count, "legacyAttempt": "unknown"}

    def job_view(job):
        return {
            "id": job.id,
            "status": job.status,
            "attempts": job.attempts,
            "reason": job.reason,
            "runId": job.run_id,
            "runAttempt": job.run_attempt,
            "createdAt": iso(job.created_at),
            "updatedAt": iso(job.updated_at),
            "nextRetryAt": iso(job.next_retry_at),
            "finishedAt": iso(job.finished_at),
        }

    def request_sync(db, repo, run_id, attempt, key, request_id):
        if key is None:
            key = "minute:" + str(int(time.time() // 60))
        if len(key) < 4 or len(key) > 128:
            raise DomainError("invalid_idempotency_key")
        job = enqueue(db, repo, run_id, attempt, key, request_id=request_id)
        db.commit()
        return job_view(job)

    @app.post(
        "/api/repositories/{repo_id}/sync", status_code=202, response_model=JobResponse
    )
    def sync(
        repo_id: str,
        body: SyncInput,
        request: Request,
        key: str | None = Header(None, alias="Idempotency-Key"),
        context=write_dependency,
    ):
        db, _, user = context
        repo = owned_repository(db, repo_id, user.id)
        return request_sync(
            db, repo, body.runId, body.runAttempt, key, request.state.request_id
        )

    @app.post("/api/runs/{run_id}/resync", status_code=202, response_model=JobResponse)
    def resync(
        run_id: str,
        request: Request,
        key: str | None = Header(None, alias="Idempotency-Key"),
        context=write_dependency,
    ):
        db, _, user = context
        run, repo = run_access(db, user, run_id)
        if not run.attempt:
            raise DomainError("legacy_attempt_unknown")
        return request_sync(
            db, repo, run.github_run_id, run.attempt, key, request.state.request_id
        )

    @app.get("/api/jobs")
    def jobs(
        repositoryId: str,
        status: str = Query(
            "all", pattern=r"^(all|queued|running|retrying|succeeded|failed|cancelled)$"
        ),
        context=access_dependency,
    ):
        db, _, user = context
        owned_repository(db, repositoryId, user.id)
        query = select(Job).where(Job.repository_id == repositoryId)
        if status != "all":
            query = query.where(Job.status == status)
        rows = db.scalars(
            query.order_by(Job.created_at.desc(), Job.id.desc()).limit(100)
        )
        return {"items": [job_view(job) for job in rows], "limit": 100}

    @app.get("/api/jobs/{job_id}", response_model=JobResponse)
    def job_detail(job_id: str, context=access_dependency):
        db, _, user = context
        job = db.get(Job, job_id)
        if not job:
            raise DomainError("job_not_found", 404)
        owned_repository(db, job.repository_id, user.id)
        return {
            **job_view(job),
            "events": [
                {"status": e.status, "reason": e.reason, "at": iso(e.created_at)}
                for e in db.scalars(
                    select(JobEvent)
                    .where(JobEvent.job_id == job.id)
                    .order_by(JobEvent.created_at, JobEvent.id)
                    .limit(100)
                )
            ],
        }

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str, context=write_dependency):
        db, _, user = context
        job = db.get(Job, job_id)
        if not job:
            raise DomainError("job_not_found", 404)
        owned_repository(db, job.repository_id, user.id)
        if job.status not in ("succeeded", "failed", "cancelled"):
            job.status, job.lease_token, job.finished_at = "cancelled", None, now()
            db.add(JobEvent(job_id=job.id, status="cancelled"))
            db.commit()
        return job_view(job)

    @app.delete("/api/runs/{run_id}")
    def remove_run(run_id: str, context=write_dependency):
        db, _, user = context
        run, repo = run_access(db, user, run_id)
        old = repo.stats_version
        db.delete(run)
        db.execute(
            update(Repository)
            .where(Repository.id == repo.id)
            .values(stats_version=Repository.stats_version + 1)
        )
        db.add(Audit(actor_id=user.id, action="run_deleted", target_id=run_id))
        db.commit()
        app.state.cache.invalidate(repo, old)
        return {"deleted": True}

    @app.post("/api/retention")
    def retention(context=write_dependency):
        db, _, user = context
        removed = 0
        for repo in db.scalars(
            select(Repository).where(Repository.owner_id == user.id)
        ):
            ids = list(
                db.scalars(
                    select(Run.id).where(
                        Run.repository_id == repo.id,
                        Run.collected_at
                        < now() - timedelta(days=settings.retention_days),
                    )
                )
            )
            for run_id in ids:
                db.delete(db.get(Run, run_id))
                removed += 1
            if ids:
                db.execute(
                    update(Repository)
                    .where(Repository.id == repo.id)
                    .values(stats_version=Repository.stats_version + 1)
                )
        db.add(
            Audit(
                actor_id=user.id, action="retention_applied", target_id="installation"
            )
        )
        db.commit()
        return {"removed": removed, "retentionDays": settings.retention_days}

    @app.get("/api/diagnostics")
    def diagnostics(context=access_dependency):
        db, _, _user = context
        db.execute(text("SELECT 1"))
        result = {
            "database": "ready",
            "cache": "unknown",
            "broker": "unknown",
            "requestLogsContainBodies": False,
            "cacheMetrics": {
                "hits": app.state.cache.hits,
                "misses": app.state.cache.misses,
                "fallbacks": app.state.cache.fallbacks,
            },
        }
        job_counts = dict(
            db.execute(
                select(Job.status, func.count())
                .join(Repository, Job.repository_id == Repository.id)
                .where(Repository.owner_id == _user.id)
                .group_by(Job.status)
            ).all()
        )
        terminal = job_counts.get("succeeded", 0) + job_counts.get("failed", 0)
        result["jobs"] = {
            "byStatus": job_counts,
            "terminalDenominator": terminal,
            "failureRate": job_counts.get("failed", 0) / terminal if terminal else None,
        }
        for name, url in [
            ("cache", settings.cache_url),
            ("broker", settings.broker_url),
        ]:
            try:
                redis.Redis.from_url(
                    url, socket_connect_timeout=0.3, socket_timeout=0.3
                ).ping()
                result[name] = "ready"
            except redis.RedisError:
                result[name] = "unavailable"
        return result

    static = Path(settings.static_dir) if settings.static_dir else None
    if static and static.exists():
        if (static / "assets").exists():
            app.mount(
                "/assets", StaticFiles(directory=static / "assets"), name="assets"
            )

        @app.get("/demo.json")
        def demo_file():
            return FileResponse(static / "demo.json")

        @app.get("/{path:path}")
        def spa(path: str):
            if path.startswith("api/"):
                raise DomainError("route_not_found", 404)
            return FileResponse(static / "index.html")

    return app

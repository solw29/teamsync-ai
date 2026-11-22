"""One transaction per import. Original report remains immutable and traceable."""

import hashlib
import json
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from teamsync.export_report import Report
from teamsync.phase2_schema import RunReport

from .errors import DomainError
from .models import (
    Audit,
    Evidence,
    Finding,
    PullRequest,
    Repository,
    Requirement,
    Run,
    Stage,
    Usage,
)


def iso(value):
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z") + (
        "Z" if value.tzinfo is None else ""
    )


def owned_repository(db, repo_id, user_id):
    repo = db.scalar(
        select(Repository).where(
            Repository.id == repo_id, Repository.owner_id == user_id, Repository.enabled
        )
    )
    if not repo:
        raise DomainError("repository_not_found", 404)
    return repo


def store_run(
    db,
    repo,
    item,
    raw,
    *,
    attempt,
    github=None,
    verification=None,
    hook=None,
    source_hash=None,
):
    payload_hash = (
        source_hash
        or hashlib.sha256(
            json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
    )
    previous = db.scalar(
        select(Run).where(
            Run.repository_id == repo.id,
            Run.github_run_id == item["runId"],
            Run.attempt == attempt,
        )
    )
    if previous:
        if (
            previous.payload_hash != payload_hash
            or previous.head_sha != item["headSha"]
        ):
            raise DomainError("immutable_run_conflict", 409)
        return previous, False
    try:
        with db.begin_nested():
            pr = db.scalar(
                select(PullRequest).where(
                    PullRequest.repository_id == repo.id,
                    PullRequest.number == item["prNumber"],
                )
            )
            if not pr:
                try:
                    with db.begin_nested():
                        pr = PullRequest(repository_id=repo.id, number=item["prNumber"])
                        db.add(pr)
                        db.flush()
                except IntegrityError:
                    pr = db.scalar(
                        select(PullRequest).where(
                            PullRequest.repository_id == repo.id,
                            PullRequest.number == item["prNumber"],
                        )
                    )
                    if not pr:
                        raise
            created = (github or {}).get("created_at", item["analyzedAt"])
            run = Run(
                repository_id=repo.id,
                pull_request_id=pr.id,
                github_run_id=item["runId"],
                attempt=attempt,
                head_sha=item["headSha"],
                schema_version=raw["schemaVersion"],
                payload_hash=payload_hash,
                finding_count=len(item["review"]["findings"]),
                analysis_status=item["status"],
                github_status=(github or {}).get("status", "unknown"),
                github_conclusion=(github or {}).get("conclusion"),
                github_created_at=datetime.fromisoformat(created),
                raw_report=raw,
                ui=item,
            )
            db.add(run)
            db.flush()
            ui = {**item, "id": run.id}
            if verification:
                ui["verification"] = verification
            run.ui = ui
            for check in (verification or {}).get("checkDetails", item["execution"]):
                db.add(
                    Stage(
                        run_id=run.id,
                        name=check["name"],
                        status=check["status"],
                        details=check,
                    )
                )
            for finding in item["review"]["findings"]:
                db.add(Finding(run_id=run.id, data=finding))
            for requirement in (verification or {}).get("requirements", []):
                db.add(
                    Requirement(
                        run_id=run.id,
                        requirement_key=requirement["id"],
                        status=requirement["status"],
                        data=requirement,
                    )
                )
            for evidence in (verification or {}).get("evidence", []):
                db.add(
                    Evidence(
                        run_id=run.id,
                        evidence_key=evidence["id"],
                        kind=evidence["kind"],
                        data=evidence,
                    )
                )
            usage = (verification or {}).get("usage", {})
            db.add(
                Usage(
                    run_id=run.id,
                    calls=usage.get("calls"),
                    input_tokens=usage.get("inputTokens"),
                    output_tokens=usage.get("outputTokens"),
                    estimated_cost=usage.get("estimatedCost"),
                )
            )
            if hook:
                hook(run)
            db.execute(
                update(Repository)
                .where(Repository.id == repo.id)
                .values(stats_version=Repository.stats_version + 1)
            )
            db.flush()
    except IntegrityError:
        # Savepoint absorbs a concurrent duplicate; no partial rows survive.
        existing = db.scalar(
            select(Run).where(
                Run.repository_id == repo.id,
                Run.github_run_id == item["runId"],
                Run.attempt == attempt,
            )
        )
        if existing and existing.payload_hash == payload_hash:
            return existing, False
        raise DomainError("immutable_run_conflict", 409) from None
    return run, True


def save_v2(db, repo, report: RunReport, github=None, hook=None):
    if report.identity.repositoryId != repo.external_id:
        raise DomainError("repository_identity_mismatch", 409)
    normalized = report.model_dump(mode="json")
    raw = getattr(report, "_source_payload", normalized)
    verification = {
        k: normalized[k]
        for k in (
            "requirements",
            "evidence",
            "checkDetails",
            "usage",
            "routing",
            "warnings",
            "impact",
        )
    }
    return store_run(
        db,
        repo,
        normalized["analysis"],
        raw,
        attempt=report.identity.runAttempt,
        github=github,
        verification=verification,
        hook=hook,
        source_hash=getattr(report, "_source_sha256", None),
    )


def import_v1(db, repo, raw):
    report = Report.model_validate(raw)
    count = 0
    for item in report.analyses:
        if item.repository.lower() != repo.full_name.lower():
            raise DomainError("repository_identity_mismatch", 409)
        _, created = store_run(
            db,
            repo,
            item.model_dump(mode="json"),
            {"schemaVersion": "1.0", "analysis": item.model_dump(mode="json")},
            attempt=0,
        )
        count += created
    db.add(Audit(actor_id=repo.owner_id, action="legacy_import", target_id=repo.id))
    return count

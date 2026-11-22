import io
import zipfile
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from server.app.artifacts import parse_archive
from server.app.errors import SyncError
from server.app.github import GitHubClient
from server.app.jobs import claim, dispatch, enqueue, process, reconcile
from server.app.models import Job, Outbox, Repository, Run, now
from teamsync.phase2_schema import RunReport


def archive(bundle, extra=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.json", bundle[0])
        z.writestr("manifest.json", bundle[1])
        if extra:
            z.writestr(*extra)
    return stream.getvalue()


def api_run(bundle):
    report = RunReport.model_validate_json(bundle[0])
    i = report.identity
    return {
        "id": i.runId,
        "run_attempt": i.runAttempt,
        "head_sha": i.headSha,
        "workflow_id": int(i.workflowId),
        "repository": {"id": i.repositoryId, "full_name": i.fullName},
        "status": "completed",
        "conclusion": "success",
        "created_at": i.observedAt.isoformat(),
    }


def test_archive_identity_and_corruption(app, repository, bundle):
    with app.state.factory() as db:
        repo = db.get(Repository, repository)
        assert (
            parse_archive(archive(bundle), repo, api_run(bundle)).identity.runAttempt
            == 1
        )
        with pytest.raises(SyncError, match="identity_mismatch"):
            parse_archive(
                archive(bundle), repo, {**api_run(bundle), "head_sha": "a" * 40}
            )
        with pytest.raises(SyncError):
            parse_archive(b"not zip", repo, api_run(bundle))
        with pytest.raises(SyncError, match="paths_or_duplicates"):
            parse_archive(archive(bundle, ("../escape", "bad")), repo, api_run(bundle))
        tampered = (bundle[0] + b" ", bundle[1])
        with pytest.raises(SyncError, match="checksum"):
            parse_archive(archive(tampered), repo, api_run(bundle))


@pytest.mark.parametrize(
    "status,headers,code,retryable",
    [
        (403, {}, "github_permission_denied", False),
        (429, {"Retry-After": "12"}, "github_rate_limit", True),
        (503, {}, "github_unavailable", True),
    ],
)
def test_remote_failures(status, headers, code, retryable):
    response = httpx.Response(status, headers=headers)
    with pytest.raises(SyncError) as raised:
        GitHubClient.check(response)
    assert raised.value.code == code and raised.value.retryable == retryable
    if status == 429:
        assert raised.value.retry_after == 12


def test_pull_never_forwards_credential_to_signed_download(
    app, repository, bundle, monkeypatch
):
    monkeypatch.setenv("FIXTURE_GITHUB_TOKEN", "never-forward-this")
    settings = app.state.settings
    settings.github_token_env = "FIXTURE_GITHUB_TOKEN"
    actual = api_run(bundle)
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host.endswith(".blob.core.windows.net"):
            assert "authorization" not in request.headers
            return httpx.Response(200, content=archive(bundle))
        assert request.headers["authorization"] == "Bearer never-forward-this"
        path = request.url.path
        if path.startswith("/repositories/"):
            return httpx.Response(200, json=actual["repository"])
        if path.endswith("/attempts/1"):
            return httpx.Response(200, json=actual)
        if path.endswith("/artifacts"):
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {
                            "id": 7,
                            "name": f"phase2-run-{actual['id']}-1",
                            "expired": False,
                            "size_in_bytes": 1000,
                        }
                    ]
                },
            )
        if path.endswith("/zip"):
            return httpx.Response(
                302,
                headers={
                    "Location": "https://fixture.blob.core.windows.net/result?signature=fixture"
                },
            )
        return httpx.Response(404)

    client = GitHubClient(settings, httpx.MockTransport(handler))
    with app.state.factory() as db:
        report, _, _ = client.sync(db.get(Repository, repository), actual["id"], 1)
    assert report.identity.runId == actual["id"]
    client.close()


def create_job(app, repository, key="same-key"):
    with app.state.factory.begin() as db:
        return enqueue(db, db.get(Repository, repository), 45015243674, 1, key).id


def test_durable_outbox_duplicate_send_and_idempotent_store(app, repository, bundle):
    job_id = create_job(app, repository)
    assert create_job(app, repository) == job_id
    sends = []

    def crash(_):
        raise RuntimeError("dispatcher crash after send")

    with pytest.raises(RuntimeError):
        dispatch(app.state.factory, sends.append, app.state.settings, after_send=crash)
    with app.state.factory() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Outbox).where(Outbox.sent_at.is_(None))
            )
            == 1
        )
    assert dispatch(app.state.factory, sends.append, app.state.settings) == 1
    assert sends == [job_id, job_id]

    class Connector:
        def sync(self, *args):
            return (
                RunReport.model_validate_json(bundle[0]),
                api_run(bundle),
                "solw29/teamsync-ai",
            )

        def close(self):
            pass

    assert (
        process(app.state.factory, job_id, app.state.settings, Connector) == "succeeded"
    )
    assert (
        process(app.state.factory, job_id, app.state.settings, Connector)
        == "duplicate_or_busy"
    )
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Run)) == 1


def test_worker_loss_lease_recovery_and_bounded_retry(app, repository):
    job_id = create_job(app, repository)
    assert claim(app.state.factory, job_id, app.state.settings)
    with app.state.factory.begin() as db:
        db.get(Job, job_id).lease_until = now() - timedelta(seconds=1)
    assert reconcile(app.state.factory, app.state.settings) == 1
    with app.state.factory() as db:
        assert db.get(Job, job_id).status == "retrying"

    class Denied:
        def sync(self, *args):
            raise SyncError("github_permission_denied")

        def close(self):
            pass

    assert (
        process(app.state.factory, job_id, app.state.settings, Denied)
        == "retrying_or_failed"
    )
    with app.state.factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "failed" and job.reason == "github_permission_denied"


def test_rate_limit_keeps_database_job_retry_state(app, repository):
    job_id = create_job(app, repository)

    class Limited:
        def sync(self, *args):
            raise SyncError("github_rate_limit", True, 20)

        def close(self):
            pass

    process(app.state.factory, job_id, app.state.settings, Limited)
    with app.state.factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "retrying" and job.attempts == 1
        assert (
            job.next_retry_at.replace(tzinfo=now().tzinfo) - now()
        ).total_seconds() > 18
        assert db.scalar(select(func.count()).select_from(Outbox)) == 2


def test_resync_is_only_database_job_not_workflow_rerun(signed, repository):
    client, headers = signed
    response = client.post(
        f"/api/repositories/{repository}/sync",
        headers={**headers, "Idempotency-Key": "click-uuid"},
        json={"runId": 45015243674, "runAttempt": 1},
    )
    assert response.status_code == 202
    duplicate = client.post(
        f"/api/repositories/{repository}/sync",
        headers={**headers, "Idempotency-Key": "click-uuid"},
        json={"runId": 45015243674, "runAttempt": 1},
    )
    assert duplicate.json()["id"] == response.json()["id"]
    assert client.get("/api/jobs/" + response.json()["id"]).json()["status"] == "queued"
    assert (
        client.post(
            "/api/jobs/" + response.json()["id"] + "/cancel", headers=headers
        ).json()["status"]
        == "cancelled"
    )


def test_queued_delivery_can_recover_if_task_never_claimed(app, repository):
    job_id = create_job(app, repository, "unclaimed")
    dispatch(app.state.factory, lambda _: None, app.state.settings)
    with app.state.factory.begin() as db:
        db.get(Job, job_id).updated_at = now() - timedelta(
            seconds=app.state.settings.lease_seconds + 1
        )
    assert reconcile(app.state.factory, app.state.settings) == 1
    with app.state.factory() as db:
        assert db.get(Job, job_id).status == "retrying"
        assert (
            db.scalar(
                select(func.count()).select_from(Outbox).where(Outbox.sent_at.is_(None))
            )
            == 1
        )


@pytest.mark.parametrize(
    "expired,size", [(True, 100), (False, 10_000_001), (False, "untrusted")]
)
def test_expired_or_oversized_metadata_is_never_downloaded(
    app, repository, bundle, monkeypatch, expired, size
):
    monkeypatch.setenv("FIXTURE_GITHUB_TOKEN", "fixture")
    app.state.settings.github_token_env = "FIXTURE_GITHUB_TOKEN"
    actual = api_run(bundle)

    def handler(request):
        if request.url.path.startswith("/repositories/"):
            return httpx.Response(200, json=actual["repository"])
        if request.url.path.endswith("/attempts/1"):
            return httpx.Response(200, json=actual)
        if request.url.path.endswith("/artifacts"):
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {
                            "id": 7,
                            "name": f"phase2-run-{actual['id']}-1",
                            "expired": expired,
                            "size_in_bytes": size,
                        }
                    ]
                },
            )
        pytest.fail("Rejected metadata must never reach download")

    client = GitHubClient(app.state.settings, httpx.MockTransport(handler))
    with (
        app.state.factory() as db,
        pytest.raises(SyncError, match="expired_or_size_limit"),
    ):
        client.sync(db.get(Repository, repository), actual["id"], 1)
    client.close()


def test_archive_compressed_bomb_and_partial_report_are_rejected(
    app, repository, bundle
):
    from server.app.artifacts import MAX_ARCHIVE

    with app.state.factory() as db:
        repo = db.get(Repository, repository)
        with pytest.raises(SyncError, match="size_limit"):
            parse_archive(b"0" * (MAX_ARCHIVE + 1), repo, api_run(bundle))
        with pytest.raises(SyncError, match="expansion_limit"):
            parse_archive(archive((b"0" * 500_001, bundle[1])), repo, api_run(bundle))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("manifest.json", bundle[1])
        with pytest.raises(SyncError, match="paths_or_duplicates"):
            parse_archive(stream.getvalue(), repo, api_run(bundle))


def test_artifact_not_yet_available_is_bounded_retry(
    app, repository, bundle, monkeypatch
):
    monkeypatch.setenv("FIXTURE_GITHUB_TOKEN", "fixture")
    app.state.settings.github_token_env = "FIXTURE_GITHUB_TOKEN"
    actual = api_run(bundle)

    def handler(request):
        if request.url.path.startswith("/repositories/"):
            return httpx.Response(200, json=actual["repository"])
        if request.url.path.endswith("/attempts/1"):
            return httpx.Response(200, json=actual)
        return httpx.Response(200, json={"artifacts": []})

    client = GitHubClient(app.state.settings, httpx.MockTransport(handler))
    with (
        app.state.factory() as db,
        pytest.raises(SyncError, match="artifact_unavailable") as error,
    ):
        client.sync(db.get(Repository, repository), actual["id"], 1)
    assert error.value.retryable
    client.close()

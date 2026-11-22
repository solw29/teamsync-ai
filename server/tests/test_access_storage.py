import copy
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from server.app.config import Settings
from server.app.models import Repository, Run, Session, Stage, User, now
from server.app.security import password_hash
from server.app.storage import save_v2
from teamsync.phase2_schema import RunReport


def test_auth_origin_csrf_and_logout(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/runs?repositoryId=unknown").status_code == 401
    assert (
        client.post(
            "/api/auth/bootstrap", headers={"Origin": "https://evil.invalid"}, json={}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/bootstrap",
            json={
                "token": "wrong",
                "username": "admin",
                "password": "fixture-password-strong",
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/bootstrap",
            json={
                "token": "fixture-bootstrap",
                "username": "admin",
                "password": "fixture-password-strong",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/auth/bootstrap",
            json={
                "token": "fixture-bootstrap",
                "username": "admin",
                "password": "fixture-password-strong",
            },
        ).status_code
        == 409
    )
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "fixture-password-strong"},
    )
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()
    assert client.post("/api/auth/logout").status_code == 403
    assert (
        client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": response.json()["csrfToken"]}
        ).status_code
        == 200
    )
    assert client.get("/api/repositories").status_code == 401


def test_legacy_twelve_idempotent_and_transaction(signed, repository, legacy, app):
    client, headers = signed
    url = f"/api/repositories/{repository}/import"
    assert client.post(url, headers=headers, json=legacy).json()["created"] == 12
    assert client.post(url, headers=headers, json=legacy).json()["created"] == 0
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Run)) == 12
        assert all(r.attempt == 0 for r in db.scalars(select(Run)))
    corrupt = copy.deepcopy(legacy)
    corrupt["analyses"][0]["headSha"] = "a" * 40
    assert client.post(url, headers=headers, json=corrupt).status_code == 409
    assert (
        client.get(
            "/api/runs", params={"repositoryId": repository, "limit": 100}
        ).json()["source"]
        == "api"
    )


def test_foreign_repo_cannot_be_read_even_with_cached_stats(signed, repository, app):
    client, _headers = signed
    with app.state.factory.begin() as db:
        user = User(
            username="other", password_hash=password_hash("other-fixture-password")
        )
        db.add(user)
        db.flush()
        repo = Repository(
            external_id=99,
            owner_id=user.id,
            full_name="other/private",
            workflow_ids=[1],
        )
        db.add(repo)
        db.flush()
        foreign = repo.id
    assert client.get(f"/api/repositories/{foreign}/stats").status_code == 404
    assert client.get("/api/runs", params={"repositoryId": foreign}).status_code == 404
    assert client.get("/api/jobs/absent").status_code == 404


def test_cursor_stable_after_new_insert_and_filter_binding(signed, repository, legacy):
    client, headers = signed
    client.post(f"/api/repositories/{repository}/import", headers=headers, json=legacy)
    first = client.get(
        "/api/runs", params={"repositoryId": repository, "limit": 3}
    ).json()
    second = client.get(
        "/api/runs",
        params={"repositoryId": repository, "limit": 3, "cursor": first["nextCursor"]},
    ).json()
    assert not ({r["id"] for r in first["items"]} & {r["id"] for r in second["items"]})
    assert (
        client.get(
            "/api/runs",
            params={
                "repositoryId": repository,
                "status": "passed",
                "cursor": first["nextCursor"],
            },
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/runs", params={"repositoryId": repository, "cursor": "broken"}
        ).status_code
        == 400
    )
    inserted = copy.deepcopy(legacy)
    inserted["analyses"] = inserted["analyses"][:1]
    inserted["analyses"][0]["runId"] = 999999999999
    assert (
        client.post(
            f"/api/repositories/{repository}/import", headers=headers, json=inserted
        ).status_code
        == 200
    )
    again = client.get(
        "/api/runs",
        params={"repositoryId": repository, "limit": 3, "cursor": first["nextCursor"]},
    ).json()
    assert [r["id"] for r in again["items"]] == [r["id"] for r in second["items"]]
    assert (
        client.get(
            "/api/runs",
            params={"repositoryId": repository, "q": "1", "sort": "reviews"},
        ).status_code
        == 200
    )


def test_v2_rollback_and_distinct_attempts(app, repository, bundle):
    import json

    report = RunReport.model_validate_json(bundle[0])

    def interrupt(_):
        raise RuntimeError("fixture interrupt")

    with pytest.raises(RuntimeError), app.state.factory.begin() as db:
        save_v2(db, db.get(Repository, repository), report, hook=interrupt)
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Stage)) == 0
    with app.state.factory.begin() as db:
        repo = db.get(Repository, repository)
        first, created = save_v2(db, repo, report)
        assert created
        duplicate, created = save_v2(db, repo, report)
        assert not created and first.id == duplicate.id
        raw = json.loads(report.model_dump_json())
        raw["identity"]["runAttempt"] = 2
        second, created = save_v2(db, repo, RunReport.model_validate(raw))
        assert created and second.id != first.id


def test_cache_fallback_commit_version_and_permission(signed, repository, legacy, app):
    client, headers = signed
    client.post(f"/api/repositories/{repository}/import", headers=headers, json=legacy)
    url = f"/api/repositories/{repository}/stats"
    first = client.get(url).json()
    second = client.get(url).json()
    assert first["total"] == 12 and second["cacheSource"] == "hit"
    app.state.cache.client.failed = True
    fallback = client.get(url).json()
    assert fallback["total"] == 12 and fallback["cacheSource"] == "database_fallback"
    app.state.cache.client.failed = False
    row = client.get("/api/runs", params={"repositoryId": repository}).json()["items"][
        0
    ]
    assert client.delete("/api/runs/" + row["id"], headers=headers).status_code == 200
    assert client.get(url).json()["total"] == 11


def test_session_expiry_and_sensitive_logs(signed, app, capsys):
    client, _ = signed
    with app.state.factory.begin() as db:
        for session in db.scalars(select(Session)):
            session.expires_at = now() - timedelta(seconds=1)
    assert client.get("/api/repositories").status_code == 401
    text = capsys.readouterr().out
    assert "fixture-password-strong" not in text and "fixture-bootstrap" not in text


def test_missing_config_is_explicit(monkeypatch, tmp_path):
    monkeypatch.delenv("TEAMSYNC_DATABASE_URL", raising=False)
    monkeypatch.setenv("TEAMSYNC_DB_PASSWORD_FILE", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="configuration missing"):
        Settings.from_env()


def test_disabled_repository_cannot_use_warmed_cache(signed, repository, legacy, app):
    client, headers = signed
    client.post(f"/api/repositories/{repository}/import", headers=headers, json=legacy)
    url = f"/api/repositories/{repository}/stats"
    assert client.get(url).status_code == 200
    assert client.get(url).json()["cacheSource"] == "hit"
    with app.state.factory.begin() as db:
        db.get(Repository, repository).enabled = False
    assert client.get(url).status_code == 404

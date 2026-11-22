import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app.cache import StatsCache
from server.app.config import Settings
from server.app.main import create_app
from server.app.models import Base


class MemoryCache:
    def __init__(self):
        self.data = {}
        self.failed = False

    def get(self, key):
        if self.failed:
            import redis

            raise redis.ConnectionError("fixture_cache_down")
        return self.data.get(key)

    def setex(self, key, ttl, value):
        if self.failed:
            import redis

            raise redis.ConnectionError("fixture_cache_down")
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


@pytest.fixture
def app():
    settings = Settings(
        database_url="sqlite:///:memory:",
        bootstrap_token="fixture-bootstrap",
        retry_base=1,
    )
    cache = StatsCache(settings, MemoryCache())
    app = create_app(settings, cache=cache)
    Base.metadata.create_all(app.state.engine)
    yield app
    app.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def signed(client):
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
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "fixture-password-strong"},
    )
    assert response.status_code == 200
    return client, {"X-CSRF-Token": response.json()["csrfToken"]}


@pytest.fixture
def repository(signed):
    client, headers = signed
    response = client.post(
        "/api/repositories",
        headers=headers,
        json={
            "externalId": 1442922359,
            "fullName": "solw29/teamsync-ai",
            "workflowIds": [426731056],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def legacy():
    return json.loads(Path("docs/report-example.json").read_text())


@pytest.fixture
def bundle():
    root = Path("D36/github-run-45015243674")
    return (root / "report.json").read_bytes(), (root / "manifest.json").read_bytes()

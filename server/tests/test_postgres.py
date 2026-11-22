"""Optional real PostgreSQL concurrency checks; refuses non-test databases."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from server.app.db import database
from server.app.models import Base, Repository, Run, User
from server.app.storage import save_v2
from teamsync.phase2_schema import RunReport


@pytest.fixture
def postgres():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL not configured; SQLite is not PostgreSQL verification"
        )
    assert make_url(url).database.endswith("_test"), "Refusing non-test database"
    engine, factory = database(url)
    Base.metadata.create_all(engine)
    with factory.begin() as db:
        user = User(username="concurrency", password_hash="fixture")
        db.add(user)
        db.flush()
        repo = Repository(
            owner_id=user.id,
            external_id=1442922359,
            full_name="solw29/teamsync-ai",
            workflow_ids=[426731056],
        )
        db.add(repo)
        db.flush()
        repo_id = repo.id
    yield factory, repo_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_real_concurrent_distinct_attempts_and_duplicates(postgres):
    factory, repo_id = postgres
    original = json.loads(Path("D36/github-run-45015243674/report.json").read_text())

    def save(attempt):
        raw = json.loads(json.dumps(original))
        raw["identity"]["runAttempt"] = attempt
        report = RunReport.model_validate(raw)
        with factory.begin() as db:
            run, created = save_v2(db, db.get(Repository, repo_id), report)
            return run.id, created

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = list(pool.map(save, [1, 2]))
    assert first[0][0] != first[1][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        again = list(pool.map(save, [1, 1]))
    assert not any(created for _, created in again)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Run)) == 2

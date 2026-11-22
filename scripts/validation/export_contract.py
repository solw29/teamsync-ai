"""Generate public API fixtures from the actual route + response models."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.app.cache import StatsCache
from server.app.config import Settings
from server.app.main import create_app
from server.app.models import Base, Repository, User
from server.app.security import password_hash
from server.app.storage import save_v2
from teamsync.phase2_schema import RunReport


class NoCache:
    def get(self, key):
        return None

    def setex(self, *args):
        pass


root = Path(__file__).resolve().parents[2]
settings = Settings(database_url="sqlite:///:memory:")
app = create_app(settings, cache=StatsCache(settings, NoCache()))
Base.metadata.create_all(app.state.engine)
report = RunReport.model_validate_json(
    (root / "docs/phase2/example-v2/report.json").read_bytes()
)
with app.state.factory.begin() as db:
    user = User(
        username="contract-admin",
        password_hash=password_hash("contract-fixture-password"),
    )
    db.add(user)
    db.flush()
    repo = Repository(
        owner_id=user.id,
        external_id=report.identity.repositoryId,
        full_name=report.identity.fullName,
        workflow_ids=[1],
    )
    db.add(repo)
    db.flush()
    run, _ = save_v2(db, repo, report)
    repo_id, run_id = repo.id, run.id
out = root / "docs/backend/contract"
out.mkdir(parents=True, exist_ok=True)
with TestClient(app) as client:
    response = client.post(
        "/api/auth/login",
        json={"username": "contract-admin", "password": "contract-fixture-password"},
    )
    assert response.status_code == 200
    for name, path in [
        ("runs", f"/api/runs?repositoryId={repo_id}"),
        ("detail", f"/api/runs/{run_id}"),
        ("stats", f"/api/repositories/{repo_id}/stats"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        (out / (name + ".json")).write_text(
            json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"
        )
(out / "openapi.json").write_text(
    json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
)
print("Public contract generated; no session or credential response exported")

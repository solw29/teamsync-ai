"""Local teamsync-phase3 validation installation only; see docs/backend/README.md."""

import json
import os
import secrets
from pathlib import Path
from urllib.parse import quote

import httpx

from server.app.config import Settings
from server.app.db import database
from server.app.github import GitHubClient
from server.app.jobs import process

root = Path(__file__).resolve().parents[2]
private = root / ".local/server"
path = private / "test_admin_password"
if not path.exists():
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(secrets.token_urlsafe(32))
password = path.read_text()
client = httpx.Client(base_url="http://127.0.0.1:8090")
if not client.get("/api/auth/setup-status").json()["initialized"]:
    r = client.post(
        "/api/auth/bootstrap",
        json={
            "username": "validation-admin",
            "password": password,
            "token": (private / "bootstrap_token").read_text().strip(),
        },
    )
    r.raise_for_status()
r = client.post(
    "/api/auth/login", json={"username": "validation-admin", "password": password}
)
r.raise_for_status()
headers = {"X-CSRF-Token": r.json()["csrfToken"]}
repos = client.get("/api/repositories").json()["items"]
if not repos:
    r = client.post(
        "/api/repositories",
        headers=headers,
        json={
            "externalId": 1442922359,
            "fullName": "solw29/teamsync-ai",
            "workflowIds": [426731056],
        },
    )
    r.raise_for_status()
    repo_id = r.json()["id"]
else:
    repo_id = repos[0]["id"]
legacy = json.loads((root / "docs/report-example.json").read_text())
r = client.post(f"/api/repositories/{repo_id}/import", headers=headers, json=legacy)
r.raise_for_status()
print("Legacy actual import", r.json()["created"])
r = client.post(
    f"/api/repositories/{repo_id}/sync",
    headers={**headers, "Idempotency-Key": "live-v2-first"},
    json={"runId": 45015243674, "runAttempt": 1},
)
r.raise_for_status()
job_id = r.json()["id"]
db_password = (private / "db_password").read_text().strip()
settings = Settings(
    database_url="postgresql+psycopg://teamsync:"
    + quote(db_password, safe="")
    + "@127.0.0.1:55432/teamsync",
    github_token_env="GH_TOKEN",
    cache_url="redis://127.0.0.1:56380/0",
)
engine, factory = database(settings.database_url)
result = process(factory, job_id, settings, lambda: GitHubClient(settings))
job = client.get("/api/jobs/" + job_id).json()
print("Actual GitHub outbound pull", result, job["status"], job["reason"])
summary = {
    "legacyCreated": 12,
    "repositoryId": repo_id,
    "jobId": job_id,
    "jobStatus": job["status"],
    "reason": job["reason"],
    "sourceRunId": 45015243674,
    "sourceAttempt": 1,
    "source": "actual GitHub API artifact; no LLM or workflow re-execution",
}
(root / "artifacts/phase3").mkdir(exist_ok=True)
(root / "artifacts/phase3/live-import.json").write_text(json.dumps(summary, indent=2))
assert job["status"] == "succeeded", job["reason"]
print("DB count", client.get(f"/api/repositories/{repo_id}/stats").json()["total"])

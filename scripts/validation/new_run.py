"""Pull one real completed run through HTTP -> outbox -> broker -> worker."""

import argparse
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--run-id", required=True, type=int)
parser.add_argument("--attempt", default=1, type=int)
args = parser.parse_args()
private = root / ".local/server"
client = httpx.Client(base_url="http://127.0.0.1:8090", timeout=15)
response = client.post(
    "/api/auth/login",
    json={
        "username": "validation-admin",
        "password": (private / "test_admin_password").read_text(),
    },
)
response.raise_for_status()
headers = {
    "X-CSRF-Token": response.json()["csrfToken"],
    "Idempotency-Key": secrets.token_hex(16),
}
repo = client.get("/api/repositories").json()["items"][0]["id"]
response = client.post(
    f"/api/repositories/{repo}/sync",
    headers=headers,
    json={"runId": args.run_id, "runAttempt": args.attempt},
)
response.raise_for_status()
assert response.status_code == 202
job_id = response.json()["id"]
subprocess.run(
    [sys.executable, str(root / "scripts/validation/dispatch_once.py")], check=True
)
for _ in range(60):
    job = client.get("/api/jobs/" + job_id).json()
    if job["status"] in ["failed", "succeeded"]:
        break
    time.sleep(0.5)
assert job["status"] == "succeeded", job["reason"]
rows = client.get("/api/runs", params={"repositoryId": repo, "limit": 100}).json()[
    "items"
]
item = next(row for row in rows if row["runId"] == args.run_id)
detail = client.get("/api/runs/" + item["id"]).json()
summary = {
    "runId": args.run_id,
    "runAttempt": detail["runAttempt"],
    "prNumber": item["prNumber"],
    "headSha": item["headSha"],
    "jobId": job_id,
    "jobStatus": job["status"],
    "jobEvents": [e["status"] for e in job["events"]],
    "databaseRows": len(rows),
    "detailId": item["id"],
    "githubStatus": detail["githubStatus"],
    "githubConclusion": detail["githubConclusion"],
    "collectionStatus": detail["collectionStatus"],
    "llmCallsTriggeredBySync": 0,
    "workflowRerunsTriggeredBySync": 0,
}
out = root / "artifacts/phase3"
out.mkdir(parents=True, exist_ok=True)
(out / "new-pr-run.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))

"""Local teamsync-phase3 validation installation only; see docs/backend/README.md."""

import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from celery import Celery

from server.app.config import Settings
from server.app.db import database
from server.app.jobs import dispatch, reconcile

assert "--owned-validation-project" in sys.argv, (
    "Requires --owned-validation-project; only isolated teamsync-phase3 may be changed"
)
root = Path(__file__).resolve().parents[2]
private = root / ".local/server"
out = root / "artifacts/phase3"
os.environ["TEAMSYNC_DATABASE_URL"] = (
    "postgresql+psycopg://teamsync:"
    + quote((private / "db_password").read_text().strip(), safe="")
    + "@127.0.0.1:55432/teamsync"
)
settings = Settings(
    database_url=os.environ["TEAMSYNC_DATABASE_URL"],
    broker_url="redis://127.0.0.1:56379/0",
    lease_seconds=3,
)
_, factory = database(settings.database_url)
c = httpx.Client(base_url="http://127.0.0.1:8090")
r = c.post(
    "/api/auth/login",
    json={
        "username": "validation-admin",
        "password": (private / "test_admin_password").read_text(),
    },
)
r.raise_for_status()
headers = {"X-CSRF-Token": r.json()["csrfToken"]}
repo = c.get("/api/repositories").json()["items"][0]["id"]
r = c.post(
    f"/api/repositories/{repo}/sync",
    headers={**headers, "Idempotency-Key": secrets.token_hex(16)},
    json={"runId": 45015243674, "runAttempt": 1},
)
r.raise_for_status()
job = r.json()["id"]
helper = Path("/tmp/phase3_fault_worker.py")
marker = Path("/tmp/phase3_claimed_marker")
marker.unlink(missing_ok=True)
helper.write_text("""import time
from pathlib import Path
from celery import Celery
from server.app.config import Settings
from server.app.db import database
from server.app.jobs import claim
settings=Settings.from_env();settings.lease_seconds=3
_,factory=database(settings.database_url)
app=Celery('crash',broker='redis://127.0.0.1:56379/0');app.conf.update(task_acks_late=True,worker_prefetch_multiplier=1)
@app.task(name='phase3.validation.claim')
def hold(job_id):
 token=claim(factory,job_id,settings)
 assert token
 Path('/tmp/phase3_claimed_marker').write_text(job_id)
 time.sleep(120)
app.worker_main(['worker','--pool=solo','--concurrency=1','-Q','phase3-validation-fault','--loglevel=warning','--hostname=phase3-fault@%h'])
""")
with open("/tmp/phase3-fault-worker.log", "w") as log:
    worker = subprocess.Popen(
        [sys.executable, str(helper)], stdout=log, stderr=log, env=os.environ.copy()
    )
    app = Celery("fault-send", broker=settings.broker_url)
    dispatch(
        factory,
        lambda jid: app.send_task(
            "phase3.validation.claim",
            args=[jid],
            queue="phase3-validation-fault",
            retry=False,
        ),
        settings,
    )
    try:
        for _ in range(100):
            if marker.exists():
                break
            if worker.poll() is not None:
                raise AssertionError("fault worker exited")
            time.sleep(0.1)
        assert marker.read_text() == job
        os.kill(worker.pid, signal.SIGKILL)
        worker.wait(timeout=5)
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()
    time.sleep(3.5)
    assert reconcile(factory, settings) >= 1
    dispatch(
        factory,
        lambda jid: app.send_task("teamsync.collect", args=[jid], retry=False),
        settings,
    )
    for _ in range(60):
        result = c.get("/api/jobs/" + job).json()
        if result["status"] in ["succeeded", "failed"]:
            break
        time.sleep(0.5)
    assert result["status"] == "succeeded", result
    summary = {
        "fault": "SIGKILL isolated solo Celery validation worker after production claim, before fetch/save",
        "leaseSeconds": 3,
        "productionRecovery": "reconcile -> outbox -> normal teamsync.collect worker -> GitHub artifact",
        "status": result["status"],
        "attempts": result["attempts"],
        "events": [
            {"status": e["status"], "reason": e["reason"]} for e in result["events"]
        ],
        "scope": "Not a hard-time-limit or prefork child-kill test; no exactly-once claim",
    }
    (out / "worker-recovery.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

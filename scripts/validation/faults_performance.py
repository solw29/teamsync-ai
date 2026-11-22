"""Local teamsync-phase3 validation installation only; see docs/backend/README.md."""

import json
import secrets
import statistics
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from celery import Celery
from sqlalchemy import event, func, select

from server.app.cache import StatsCache
from server.app.config import Settings
from server.app.db import database
from server.app.jobs import dispatch
from server.app.models import Outbox, Repository, Run, now

assert "--owned-validation-project" in sys.argv, (
    "Requires --owned-validation-project; only isolated teamsync-phase3 may be changed"
)
root = Path(__file__).resolve().parents[2]
private = root / ".local/server"
out = root / "artifacts/phase3"
settings = Settings(
    database_url="postgresql+psycopg://teamsync:"
    + quote((private / "db_password").read_text().strip(), safe="")
    + "@127.0.0.1:55432/teamsync",
    broker_url="redis://127.0.0.1:56379/0",
    cache_url="redis://127.0.0.1:56380/0",
    deployment_id="phase3-measure",
)
engine, factory = database(settings.database_url)
c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=15)
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
results = {}


def docker(*args):
    subprocess.run(
        ["docker", *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def waitjob(job):
    for _ in range(40):
        j = c.get("/api/jobs/" + job).json()
        if j["status"] in ["succeeded", "failed"]:
            return j
        time.sleep(0.5)
    raise AssertionError("worker did not finish")


# Stop cache alone. The independent broker and database must still serve.
docker("stop", "teamsync-phase3-cache-1")
try:
    r = c.get(f"/api/repositories/{repo}/stats")
    r.raise_for_status()
    assert r.json()["cacheSource"] == "database_fallback"
    d = c.get("/api/diagnostics").json()
    assert d["broker"] == "ready"
    results["cacheFailure"] = {
        "http": r.status_code,
        "source": r.json()["cacheSource"],
        "broker": d["broker"],
    }
finally:
    docker("start", "teamsync-phase3-cache-1")
# An accepted request remains durable while Redis broker is unavailable.
app = Celery("fault-check", broker=settings.broker_url)
app.conf.broker_transport_options = {
    "socket_connect_timeout": 0.5,
    "socket_timeout": 0.5,
}
send = lambda j: app.send_task("teamsync.collect", args=[j], retry=False)
docker("stop", "teamsync-phase3-queue-1")
try:
    r = c.post(
        f"/api/repositories/{repo}/sync",
        headers={**headers, "Idempotency-Key": secrets.token_hex(16)},
        json={"runId": 45015243674, "runAttempt": 1},
    )
    assert r.status_code == 202
    jid = r.json()["id"]
    dispatch(factory, send, settings)
    with factory() as db:
        entry = db.scalar(select(Outbox).where(Outbox.job_id == jid))
        assert entry.sent_at is None and entry.send_attempts == 1
    results["brokerFailure"] = {
        "acceptedHTTP": 202,
        "durableOutbox": True,
        "publishAttempts": 1,
    }
finally:
    docker("start", "teamsync-phase3-queue-1")
# Avoid waiting the production backoff in this isolated validation installation.
with factory.begin() as db:
    entry = db.scalar(select(Outbox).where(Outbox.job_id == jid))
    entry.available_at = now()
dispatch(factory, send, settings)
j = waitjob(jid)
assert j["status"] == "succeeded"
results["brokerRecovery"] = {
    "status": j["status"],
    "events": [e["status"] for e in j["events"]],
}
# Database readiness and pool reconnect.
docker("stop", "teamsync-phase3-db-1")
try:
    r = c.get("/ready")
    assert r.status_code == 503
    results["databaseFailure"] = {"readinessHTTP": r.status_code}
finally:
    docker("start", "teamsync-phase3-db-1")
for _ in range(40):
    if c.get("/ready").status_code == 200:
        break
    time.sleep(0.5)
r = c.get("/runs")  # SPA path does not alter data
with factory() as db:
    results["databaseRecovery"] = {
        "runCount": db.scalar(select(func.count()).select_from(Run))
    }
# Real stats timings on the same 13-row repository, not a scale claim.
cache = StatsCache(settings)
query_count = [0]


def count(*args):
    query_count[0] += 1


event.listen(engine, "before_cursor_execute", count)
measure = {}
with factory() as db:
    repo_obj = db.get(Repository, repo)
    for mode in ["database", "warm_cache"]:
        cache.stats(db, repo_obj, enabled=True)
        query_count[0] = 0
        times = []
        for _ in range(100):
            start = time.perf_counter()
            value = cache.stats(db, repo_obj, enabled=mode == "warm_cache")
            times.append((time.perf_counter() - start) * 1000)
        times.sort()
        measure[mode] = {
            "samples": 100,
            "p50Ms": round(statistics.median(times), 3),
            "p95Ms": round(times[94], 3),
            "sqlStatements": query_count[0],
            "lastSource": value["cacheSource"],
        }
measure["rows"] = results["databaseRecovery"]["runCount"]
measure["environment"] = (
    "local PostgreSQL17.5 / Redis7.4.4 / Python3.12, same process and repository"
)
results["statsMeasurement"] = measure
(out / "faults-performance.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))

import sys

"""Local teamsync-phase3 validation installation only; see docs/backend/README.md."""
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine, text

assert "--owned-validation-project" in sys.argv, (
    "Requires --owned-validation-project; only isolated teamsync-phase3 may be changed"
)
root = Path(__file__).resolve().parents[2]
out = root / "artifacts/phase3"
backup = out / "private-backup.dump"
fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "wb") as stream:
    subprocess.run(
        [
            "docker",
            "exec",
            "teamsync-phase3-db-1",
            "pg_dump",
            "-U",
            "teamsync",
            "-d",
            "teamsync",
            "-Fc",
        ],
        stdout=stream,
        check=True,
    )
subprocess.run(
    [
        "docker",
        "exec",
        "teamsync-phase3-db-1",
        "createdb",
        "-U",
        "teamsync",
        "teamsync_restore",
    ],
    check=True,
)
with backup.open("rb") as stream:
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "teamsync-phase3-db-1",
            "pg_restore",
            "-U",
            "teamsync",
            "-d",
            "teamsync_restore",
            "--no-owner",
        ],
        stdin=stream,
        check=True,
    )
base = (
    "postgresql+psycopg://teamsync:"
    + quote((root / ".local/server/db_password").read_text().strip(), safe="")
    + "@127.0.0.1:55432/"
)
counts = {}
for name in ["teamsync", "teamsync_restore"]:
    engine = create_engine(base + name)
    with engine.connect() as db:
        counts[name] = {
            table: db.execute(text("SELECT count(*) FROM " + table)).scalar_one()
            for table in ["repositories", "runs", "findings", "users", "jobs"]
        }
    engine.dispose()
assert counts["teamsync"] == counts["teamsync_restore"]
(out / "backup-restore.json").write_text(
    json.dumps(
        {
            "format": "pg_dump custom",
            "privateDumpCommitted": False,
            "counts": counts,
            "match": True,
            "warning": "Validation restore only. Invalidate restored sessions before real use.",
        },
        indent=2,
    )
)
# Synthetic isolated index benchmark; never drops production indexes.
engine = create_engine(base + "teamsync_test")
measurement = {}
with engine.begin() as db:
    db.execute(
        text(
            "CREATE TABLE phase3_index_measure (id bigint primary key, repository_id int, created_at timestamptz)"
        )
    )
    db.execute(
        text(
            "INSERT INTO phase3_index_measure SELECT n, n % 100, now() - (n || ' seconds')::interval FROM generate_series(1,100000) n"
        )
    )
    db.execute(text("ANALYZE phase3_index_measure"))
    query = "SELECT id, created_at FROM phase3_index_measure WHERE repository_id=42 ORDER BY created_at DESC,id DESC LIMIT 20"
    for mode in ["without_composite_index", "with_composite_index"]:
        if mode.startswith("with_"):
            db.execute(
                text(
                    "CREATE INDEX ON phase3_index_measure (repository_id,created_at DESC,id DESC)"
                )
            )
        db.execute(text(query)).all()
        times = []
        for _ in range(30):
            start = time.perf_counter()
            db.execute(text(query)).all()
            times.append((time.perf_counter() - start) * 1000)
        plan = db.execute(
            text("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) " + query)
        ).scalar_one()
        measurement[mode] = {
            "samples": 30,
            "p50Ms": round(statistics.median(times), 3),
            "p95Ms": round(sorted(times)[28], 3),
            "plan": plan,
        }
    db.execute(text("DROP TABLE phase3_index_measure"))
measurement["environment"] = (
    "local PostgreSQL17.5, isolated teamsync_test table, 100000 generated rows / 100 repositories; warm reads; not actual traffic"
)
(out / "index-measurement.json").write_text(json.dumps(measurement, indent=2))
print("Actual backup/restore row counts match; synthetic index measurement recorded")

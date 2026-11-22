"""Local teamsync-phase3 validation installation only; see docs/backend/README.md."""

from pathlib import Path
from urllib.parse import quote

from celery import Celery

from server.app.config import Settings
from server.app.db import database
from server.app.jobs import dispatch

password = (
    (Path(__file__).resolve().parents[2] / ".local/server/db_password")
    .read_text()
    .strip()
)
settings = Settings(
    database_url="postgresql+psycopg://teamsync:"
    + quote(password, safe="")
    + "@127.0.0.1:55432/teamsync",
    broker_url="redis://127.0.0.1:56379/0",
)
_, factory = database(settings.database_url)
client = Celery("dispatch", broker=settings.broker_url)
dispatch(
    factory,
    lambda job: client.send_task("teamsync.collect", args=[job], retry=False),
    settings,
)

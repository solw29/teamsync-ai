import time

from kombu.exceptions import KombuError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .config import Settings
from .db import database
from .errors import SyncError
from .github import GitHubClient
from .jobs import discover, dispatch, reconcile
from .models import Repository, SyncCursor
from .telemetry import record


def main():
    from .worker import celery_app

    settings = Settings.from_env()
    _, factory = database(settings.database_url)
    last_scan = 0
    while True:
        try:
            reconcile(factory, settings)
            dispatch(
                factory,
                lambda job_id: celery_app.send_task(
                    "teamsync.collect", args=[job_id], retry=False
                ),
                settings,
            )
            if time.monotonic() - last_scan >= 60:
                client = None
                try:
                    client = GitHubClient(settings)
                    discover(factory, client, settings)
                except SyncError as error:
                    with factory.begin() as db:
                        for repo in db.scalars(
                            select(Repository).where(Repository.enabled)
                        ):
                            cursor = db.get(SyncCursor, repo.id)
                            if not cursor:
                                cursor = SyncCursor(repository_id=repo.id)
                                db.add(cursor)
                            cursor.last_error = error.code
                    record("discovery_unavailable", reason=error.code)
                finally:
                    if client:
                        client.close()
                last_scan = time.monotonic()
        except (SQLAlchemyError, KombuError, OSError):
            # No credentials, report body or client exception text enters logs.
            print("scheduler_cycle_unavailable", flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()

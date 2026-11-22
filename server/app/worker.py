from celery import Celery

from .cache import StatsCache
from .config import Settings
from .db import database
from .github import GitHubClient
from .jobs import process

settings = Settings.from_env()
_, factory = database(settings.database_url)
celery_app = Celery("teamsync", broker=settings.broker_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=150,
    task_soft_time_limit=120,
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    broker_transport_options={
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
        "visibility_timeout": 300,
    },
)


@celery_app.task(name="teamsync.collect")
def collect(job_id: str):
    return process(
        factory, job_id, settings, lambda: GitHubClient(settings), StatsCache(settings)
    )

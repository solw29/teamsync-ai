"""Single-install configuration. Credential values never appear in repr or API."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote


@dataclass
class Settings:
    database_url: str = field(repr=False)
    bootstrap_token: str = field(default="", repr=False)
    github_token_file: str = "/run/secrets/github_read_token"
    github_token_env: str = ""
    broker_url: str = field(default="redis://queue:6379/0", repr=False)
    cache_url: str = field(default="redis://cache:6379/0", repr=False)
    deployment_id: str = "local"
    origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8090",
        "http://127.0.0.1:8090",
    )
    cookie_secure: bool = False
    session_seconds: int = 28800
    cache_ttl: int = 30
    lease_seconds: int = 300
    max_attempts: int = 6
    retry_base: int = 15
    retention_days: int = 90
    static_dir: str = ""

    @classmethod
    def from_env(cls):
        url = os.environ.get("TEAMSYNC_DATABASE_URL")
        if not url:
            try:
                password = (
                    Path(
                        os.environ.get(
                            "TEAMSYNC_DB_PASSWORD_FILE", "/run/secrets/db_password"
                        )
                    )
                    .read_text()
                    .strip()
                )
            except OSError:
                raise ValueError(
                    "Database configuration missing; see backend setup instructions"
                ) from None
            url = f"postgresql+psycopg://teamsync:{quote(password, safe='')}@db:5432/teamsync"
        bootstrap = os.environ.get("TEAMSYNC_BOOTSTRAP_TOKEN", "")
        path = Path(
            os.environ.get("TEAMSYNC_BOOTSTRAP_FILE", "/run/secrets/bootstrap_token")
        )
        if not bootstrap and path.exists():
            bootstrap = path.read_text().strip()
        return cls(
            database_url=url,
            bootstrap_token=bootstrap,
            github_token_file=os.environ.get(
                "TEAMSYNC_GITHUB_TOKEN_FILE", "/run/secrets/github_read_token"
            ),
            github_token_env=os.environ.get("TEAMSYNC_GITHUB_TOKEN_ENV", ""),
            broker_url=os.environ.get("TEAMSYNC_BROKER_URL", "redis://queue:6379/0"),
            cache_url=os.environ.get("TEAMSYNC_CACHE_URL", "redis://cache:6379/0"),
            deployment_id=os.environ.get("TEAMSYNC_DEPLOYMENT_ID", "local"),
            cookie_secure=os.environ.get("TEAMSYNC_COOKIE_SECURE", "false") == "true",
            static_dir=os.environ.get("TEAMSYNC_STATIC_DIR", ""),
        )

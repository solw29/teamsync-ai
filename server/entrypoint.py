"""Read 0600 file-mounted secrets at startup, then permanently drop privileges.

Local Compose file secrets cannot remap uid/mode. Values stay only in the
necessary process environment; never emit them or pass them as argv.
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote


def read(path):
    file = Path(path)
    return file.read_text().strip() if file.exists() else ""


if not os.environ.get("TEAMSYNC_DATABASE_URL"):
    password = read("/run/secrets/db_password")
    if password:
        os.environ["TEAMSYNC_DATABASE_URL"] = (
            "postgresql+psycopg://teamsync:"
            + quote(password, safe="")
            + "@db:5432/teamsync"
        )
bootstrap = read("/run/secrets/bootstrap_token")
if bootstrap:
    os.environ["TEAMSYNC_BOOTSTRAP_TOKEN"] = bootstrap
credential = read("/run/secrets/github_read_token")
if credential:
    os.environ["TEAMSYNC_RUNTIME_GITHUB_TOKEN"] = credential
    os.environ["TEAMSYNC_GITHUB_TOKEN_ENV"] = "TEAMSYNC_RUNTIME_GITHUB_TOKEN"
if os.getuid() == 0:
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)
os.execvp(sys.argv[1], sys.argv[1:])

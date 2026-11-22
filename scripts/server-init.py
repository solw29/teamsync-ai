"""Create local development secrets once. Never overwrites or prints values."""

import os
import secrets
from pathlib import Path

root = Path(".local/server")
root.mkdir(parents=True, exist_ok=True, mode=0o700)
for name in ["db_password", "bootstrap_token"]:
    path = root / name
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(name + ": existing file preserved")
        continue
    with os.fdopen(descriptor, "w") as stream:
        stream.write(secrets.token_urlsafe(32))
    print(name + ": created (value hidden)")

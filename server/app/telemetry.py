"""Allowlisted operational events. Never serialize exceptions, bodies or headers."""

import json
import re

FIELDS = {
    "jobId",
    "runId",
    "requestId",
    "attempt",
    "durationMs",
    "queueWaitMs",
    "reason",
    "count",
}


def record(event, **fields):
    safe = {}
    for key, value in fields.items():
        if key not in FIELDS or value is None:
            continue
        if (
            isinstance(value, (int, float))
            or isinstance(value, str)
            and len(value) <= 80
            and re.fullmatch(r"[A-Za-z0-9_-]+", value)
        ):
            safe[key] = value
    print(json.dumps({"event": event, **safe}), flush=True)

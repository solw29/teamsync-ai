"""Bounded added-line input; excluded and truncated input is explicit."""
import fnmatch
import re
import subprocess

EXCLUDED = ("*.lock", "*-lock.json", "*.min.js", "*.svg", "dist/*", "build/*")


def parse_diff(patch: str, max_lines: int = 300, max_chars: int = 24000) -> dict:
    lines, positions, excluded = [], {}, set()
    path, number, truncated = None, 0, False
    used = 0
    for raw in patch.splitlines():
        if raw.startswith("diff --git "):
            path = None
        elif raw.startswith("+++ b/"):
            path = raw[6:]
            if any(fnmatch.fnmatch(path, pattern) for pattern in EXCLUDED):
                excluded.add(path)
                path = None
        elif raw.startswith("@@"):
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if match:
                number = int(match[1])
        elif path and raw.startswith("+"):
            entry = {"file": path, "line": number, "code": raw[1:]}
            cost = len(path) + len(raw) + 30
            if len(lines) >= max_lines or used + cost > max_chars:
                truncated = True
            else:
                lines.append(entry)
                positions.setdefault(path, []).append(number)
                used += cost
            number += 1
        elif path and raw.startswith(" "):
            number += 1
    return {"lines": lines, "positions": positions, "excluded": sorted(excluded),
            "truncated": truncated}


def collect(base: str, head: str, cwd: str = ".") -> dict:
    # Only resolved commit IDs are accepted, never command options from input.
    for ref in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            raise ValueError("Expected full commit SHA")
    patch = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--no-textconv", "--unified=0", f"{base}...{head}", "--"],
        cwd=cwd, check=True, capture_output=True, text=True, timeout=30,
    ).stdout
    return parse_diff(patch)

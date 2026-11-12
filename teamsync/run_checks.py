import subprocess
import sys


def run_checks(cwd: str) -> list[dict]:
    results = []
    for name, command in [("ruff", [sys.executable, "-m", "ruff", "check", "."]),
                          ("pytest", [sys.executable, "-m", "pytest", "-q"])]:
        try:
            process = subprocess.run(command, check=False, cwd=cwd, capture_output=True, text=True, timeout=120)
            status = "passed" if process.returncode == 0 else "failed"
            if process.returncode not in (0, 1):
                status = "error"
            results.append({"name": name, "status": status, "exit_code": process.returncode,
                            "summary": (process.stdout + process.stderr)[-6000:]})
        except (OSError, subprocess.TimeoutExpired):
            results.append({"name": name, "status": "error", "summary": "Check unavailable or timed out"})
    return results

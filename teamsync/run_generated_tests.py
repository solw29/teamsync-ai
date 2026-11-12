"""Run only inside the separate disposable, secret-free Actions job.

A subprocess timeout is not a security sandbox. Never invoke on a developer
machine containing credentials; model-generated Python is arbitrary code.
"""
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .schema import Review


def execute(review: Review, cwd: str) -> list[dict]:
    if os.environ.get("TEAMSYNC_DISPOSABLE_RUNNER") != "1":
        return [{"status": "not_run", "reason": "Disposable secret-free runner required"}]
    results = []
    with tempfile.TemporaryDirectory(prefix="teamsync-tests-") as directory:
        for index, draft in enumerate(review.tests):
            path = Path(directory) / f"test_draft_{index}.py"
            path.write_text(draft.code, encoding="utf-8")
            environment = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(cwd).resolve()),
                           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "HOME": directory}
            try:
                with tempfile.TemporaryFile(mode="w+") as output:
                    report = Path(directory) / f"report_{index}.xml"
                    process = subprocess.Popen(
                        [sys.executable, "-m", "pytest", "-q", "-c", "/dev/null", f"--junitxml={report}", str(path)],
                        cwd=cwd, env=environment, stdout=output, stderr=output,
                        start_new_session=True,
                    )
                    try:
                        process.wait(timeout=30)
                        status = {0: "passed", 1: "failed"}.get(process.returncode, "environment_error")
                    finally:
                        # Also remove background descendants after normal exit.
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait()
                if report.exists() and status == "failed":
                    try:
                        failures = ET.parse(report).getroot().iter("failure")
                        if any("NameError" in (f.text or "") or "ModuleNotFoundError" in (f.text or "") for f in failures):
                            status = "environment_error"
                    except ET.ParseError:
                        status = "environment_error"
                results.append({"target": draft.target, "status": status})
            except (OSError, subprocess.TimeoutExpired):
                results.append({"target": draft.target, "status": "environment_error"})
    return results

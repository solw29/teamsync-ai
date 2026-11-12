import argparse
import json
import os
from pathlib import Path

import httpx

from .analyze import analyze
from .collect_diff import collect
from .discord_notify import notify
from .github_comments import render, upsert
from .run_checks import run_checks
from .run_generated_tests import execute
from .schema import Review


def read(path):
    file = Path(path)
    if file.stat().st_size > 2_000_000:
        raise ValueError("Artifact exceeds input limit")
    return json.loads(file.read_text())


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["collect", "analyze", "execute", "publish"])
    parser.add_argument("--target", default="target")
    args = parser.parse_args()
    if args.stage == "collect":
        write("artifacts/checks.json", run_checks(args.target))
        write("artifacts/diff.json", collect(os.environ["BASE_SHA"], os.environ["HEAD_SHA"], args.target))
    elif args.stage == "analyze":
        write("artifacts/analysis.json", analyze(read("artifacts/diff.json"), read("artifacts/checks.json")))
    elif args.stage == "execute":
        analysis = read("artifacts/analysis.json")
        result = execute(Review.model_validate(analysis["review"]), args.target) if analysis.get("review") else []
        write("artifacts/generated.json", result)
    else:
        event = read(os.environ["GITHUB_EVENT_PATH"])
        pr = event["pull_request"]
        repository = os.environ["GITHUB_REPOSITORY"]
        checks = read("artifacts/checks.json")
        diff = read("artifacts/diff.json")
        analysis = read("artifacts/analysis.json") if Path("artifacts/analysis.json").exists() else {"status": "not_run"}
        generated = read("artifacts/generated.json") if Path("artifacts/generated.json").exists() else []
        status = "not_configured"
        if os.environ.get("DISCORD_WEBHOOK_URL"):
            status = notify(os.environ["DISCORD_WEBHOOK_URL"],
                            f"https://github.com/{repository}/pull/{int(pr['number'])}", analysis["status"])
        body = render(checks, analysis, diff, generated) + f"\nDiscord: {status}"
        with httpx.Client(headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}, timeout=20) as client:
            upsert(client, repository, int(pr["number"]), body)


if __name__ == "__main__":
    main()

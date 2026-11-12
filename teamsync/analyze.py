import json
import os
from importlib.resources import files

import httpx

from .schema import Review


def analyze(diff: dict, checks: list) -> dict:
    if not os.environ.get("LLM_API_KEY"):
        return {"status": "missing_input", "review": None, "error": "LLM_API_KEY not configured"}
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
                json={"model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                      "messages": [
                          {"role": "system", "content": files("teamsync").joinpath("prompts/review.txt").read_text()},
                          {"role": "user", "content": json.dumps({"diff": diff["lines"], "checks": checks})}],
                      "response_format": {"type": "json_schema", "json_schema": {
                          "name": "review", "strict": True, "schema": Review.model_json_schema()}},
                      "max_completion_tokens": 6000},
            )
            response.raise_for_status()
            review = Review.model_validate_json(response.json()["choices"][0]["message"]["content"])
        return {"status": "passed", "review": review.model_dump()}
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        # Do not expose response bodies, authentication headers or secret URLs.
        return {"status": "error", "review": None, "error": "LLM request or schema validation failed"}

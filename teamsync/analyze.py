import json
import os
from importlib.resources import files

import httpx

from .schema import Review


def analyze(diff: dict, checks: list, *, contracts: list | None = None, max_tokens: int = 6000, max_input_chars: int | None = None) -> dict:
    if not os.environ.get("LLM_API_KEY"):
        return {"status": "missing_input", "review": None, "error": "LLM_API_KEY not configured",
                "usage": {"calls": 0, "inputTokens": None, "outputTokens": None, "estimatedCost": None}}
    payload = {"diff": diff["lines"], "checks": checks, "explicit_contracts": contracts or []}
    serialized = json.dumps(payload, ensure_ascii=False)
    if max_input_chars is not None and len(serialized) > max_input_chars:
        return {"status": "error", "review": None, "error": "model_input_limit_exceeded",
                "usage": {"calls": 0, "inputTokens": None, "outputTokens": None, "estimatedCost": None}}
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
                json={"model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                      "messages": [
                          {"role": "system", "content": files("teamsync").joinpath("prompts/review.txt").read_text()},
                          {"role": "user", "content": serialized}],
                      "response_format": {"type": "json_schema", "json_schema": {
                          "name": "review", "strict": True, "schema": Review.model_json_schema()}},
                      "max_completion_tokens": max_tokens},
            )
            response.raise_for_status()
            review = Review.model_validate_json(response.json()["choices"][0]["message"]["content"])
        usage = response.json().get('usage') or {}
        return {"status": "passed", "review": review.model_dump(),
                "model": response.json().get("model"), "requestedModel": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                "usage": {"calls": 1, "inputTokens": usage.get('prompt_tokens'),
                          "outputTokens": usage.get('completion_tokens'), "estimatedCost": None}}
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        # Do not expose response bodies, authentication headers or secret URLs.
        return {"status": "error", "review": None, "error": "LLM request or schema validation failed"}

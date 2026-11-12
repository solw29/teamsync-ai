import json

import httpx
import pytest
from pydantic import ValidationError

from teamsync.analyze import analyze
from teamsync.collect_diff import parse_diff
from teamsync.github_comments import MARKER, render, upsert
from teamsync.run_generated_tests import execute
from teamsync.schema import Review
from teamsync.validate_findings import validate

PATCH = '''diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,2 +1,3 @@
 context
-old
+new
+more
'''


def review():
    return Review(summary="요약", findings=[
        {"file": "a.py", "line": n, "evidence": "근거", "suggestion": "제안"}
        for n in (1, 2, 3, 99)], tests=[])


def test_added_lines_only():
    diff = parse_diff(PATCH)
    assert diff["positions"] == {"a.py": [2, 3]}
    result, dropped = validate(review(), diff)
    assert [f.line for f in result.findings] == [2, 3]
    assert dropped == 2


def test_limits_and_exclusions():
    assert parse_diff(PATCH, max_lines=1)["truncated"]
    assert parse_diff(PATCH, max_chars=1)["positions"] == {}
    diff = parse_diff(PATCH.replace("a.py", "package-lock.json"))
    assert not diff["lines"]
    assert diff["excluded"] == ["package-lock.json"]


def test_schema_rejects_commands_and_invalid_line():
    data = review().model_dump()
    data["command"] = "arbitrary"
    with pytest.raises(ValidationError):
        Review.model_validate(data)
    data.pop("command")
    data["findings"][0]["line"] = 0
    with pytest.raises(ValidationError):
        Review.model_validate(data)


def test_missing_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert analyze(parse_diff(PATCH), [])["status"] == "missing_input"


def test_generated_execution_refuses_local_machine(monkeypatch):
    monkeypatch.delenv("TEAMSYNC_DISPOSABLE_RUNNER", raising=False)
    assert execute(review(), ".")[0]["status"] == "not_run"


def test_render_filters_again_and_escapes():
    data = review().model_dump()
    data["summary"] = "<script>@everyone</script>"
    body = render([], {"status": "passed", "review": data}, parse_diff(PATCH), [])
    assert "2건 제외" in body
    assert "a.py:99" not in body
    assert "<script>" not in body
    assert "@everyone" not in body
    assert body.startswith(MARKER)


@pytest.mark.parametrize("exists", [True, False])
def test_comment_upsert(exists):
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[
                {"id": 4, "body": MARKER, "user": {"login": "human"}},
                *([{"id": 7, "body": MARKER, "user": {"login": "github-actions[bot]"}}] if exists else [])])
        assert json.loads(request.content)["body"] == "report"
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        upsert(client, "owner/repo", 1, "report")
    assert requests[-1].method == ("PATCH" if exists else "POST")


def test_analysis_api_failure_redacts(monkeypatch):
    import teamsync.analyze as module

    monkeypatch.setenv("LLM_API_KEY", "test-only-secret")

    def reject(*args, **kwargs):
        raise httpx.ConnectError("sensitive transport details")

    monkeypatch.setattr(httpx.Client, "post", reject)
    result = module.analyze(parse_diff(PATCH), [])
    assert result["status"] == "error"
    assert "secret" not in json.dumps(result)
    assert "sensitive" not in json.dumps(result)


def test_analysis_schema_response(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only-secret")

    def respond(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://api.openai.com"),
                              json={"choices": [{"message": {"content": review().model_dump_json()}}]})

    monkeypatch.setattr(httpx.Client, "post", respond)
    assert analyze(parse_diff(PATCH), [])["status"] == "passed"


@pytest.mark.parametrize("code,expected", [
    ("def test_ok(): assert 1 == 1", "passed"),
    ("def test_bad(): assert 1 == 2", "failed"),
    ("def test_syntax(:", "environment_error"),
])
def test_runner_known_harmless_fixtures(monkeypatch, tmp_path, code, expected):
    # Fixed fixtures only; never run arbitrary model output on the developer machine.
    monkeypatch.setenv("TEAMSYNC_DISPOSABLE_RUNNER", "1")
    draft = Review(summary="fixture", findings=[], tests=[{
        "target": "fixture", "code": code, "purpose": "runner status regression"}])
    assert execute(draft, str(tmp_path))[0]["status"] == expected


def test_discord_payload_mentions_disabled(monkeypatch):
    from teamsync.discord_notify import notify

    def post(url, **kwargs):
        assert kwargs["json"]["allowed_mentions"] == {"parse": []}
        return httpx.Response(204, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    assert notify("https://discord.com/api/webhooks/test/test", "https://github.com/o/r/pull/1", "passed") == "passed"
    assert notify("https://evil.example/api/webhooks/test/test", "", "passed") == "error"


def test_missing_import_is_environment_error(monkeypatch, tmp_path):
    monkeypatch.setenv("TEAMSYNC_DISPOSABLE_RUNNER", "1")
    draft = Review(summary="fixture", findings=[], tests=[{
        "target": "missing", "code": "def test_missing(): assert missing_function(0) is None",
        "purpose": "missing import classification"}])
    assert execute(draft, str(tmp_path))[0]["status"] == "environment_error"

import html

import httpx

from .schema import Review
from .validate_findings import validate

MARKER = "<!-- teamsync-ai -->"


def text(value: object) -> str:
    return html.escape(str(value)).replace("@", "＠").replace("`", "ˋ")


def render(checks: list, analysis: dict, diff: dict, generated: list) -> str:
    parts = [MARKER, "## TeamSync AI", "### 검사 결과"]
    for check in checks:
        parts.append(f"- {text(check['name'])}: {text(check['status'])}")
    parts.append(f"\nAI 분석: {text(analysis.get('status', 'not_run'))}")
    if analysis.get("review"):
        review, dropped = validate(Review.model_validate(analysis["review"]), diff)
        parts.extend([text(review.summary), f"근거 확인 실패로 {dropped}건 제외"])
        for finding in review.findings:
            parts.append(f"- {text(finding.file)}:{finding.line} — {text(finding.evidence)} / {text(finding.suggestion)}")
        for draft in review.tests:
            parts.extend([f"\n테스트 초안: {text(draft.target)} — {text(draft.purpose)}",
                          "<pre>" + text(draft.code) + "</pre>"])
    parts.extend(["\n### 생성 테스트 실행 상태", text(generated or "미실행"),
                  "통과는 실행 가능 여부만 의미하며 품질·버그 검출을 보증하지 않습니다.",
                  f"diff 일부 생략: {bool(diff.get('truncated'))}; 제외 파일: {len(diff.get('excluded', []))}"])
    return "\n".join(parts)[:60000]


def upsert(client: httpx.Client, repository: str, number: int, body: str) -> None:
    endpoint = f"https://api.github.com/repos/{repository}/issues/{number}/comments"
    page = 1
    while True:
        response = client.get(endpoint, params={"per_page": 100, "page": page})
        response.raise_for_status()
        comments = response.json()
        for comment in comments:
            if (comment.get("user", {}).get("login") == "github-actions[bot]"
                    and comment.get("body", "").startswith(MARKER)):
                response = client.patch(
                    f"https://api.github.com/repos/{repository}/issues/comments/{int(comment['id'])}",
                    json={"body": body})
                response.raise_for_status()
                return
        if len(comments) < 100:
            break
        page += 1
    response = client.post(endpoint, json={"body": body})
    response.raise_for_status()

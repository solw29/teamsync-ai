from urllib.parse import urlparse

import httpx


def notify(url: str, pr_url: str, status: str) -> str:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "discord.com"
            or not parsed.path.startswith("/api/webhooks/") or parsed.port not in (None, 443)):
        return "error"
    try:
        response = httpx.post(url, json={"content": f"TeamSync AI 분석: {status}\n{pr_url}",
                                        "allowed_mentions": {"parse": []}},
                              timeout=15, follow_redirects=False)
        response.raise_for_status()
        return "passed"
    except httpx.HTTPError:
        return "error"

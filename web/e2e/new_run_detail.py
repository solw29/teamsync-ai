"""Verify the actual newly collected PR run in the isolated validation UI."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[2]
data = json.loads((root / "artifacts/phase3/new-pr-run.json").read_text())
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8090/dashboard")
    page.get_by_label("사용자 이름").fill("validation-admin")
    page.get_by_label("비밀번호").fill(
        (root / ".local/server/test_admin_password").read_text()
    )
    page.get_by_role("button", name="로그인", exact=True).click()
    expect(page.locator("tbody tr")).to_have_count(14)
    page.goto("http://127.0.0.1:8090/pulls/" + data["detailId"])
    expect(page.get_by_role("button", name="기존 결과 재수집")).to_be_enabled()
    expect(page.get_by_text(str(data["runId"]), exact=False).first).to_be_visible()
    page.get_by_role("tab", name="Evidence", exact=True).click()
    expect(page.get_by_role("heading", name="요구사항과 판정 근거")).to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="기존 결과 재수집")).to_be_enabled()
    page.screenshot(
        path=str(root / "artifacts/phase3/new-pr-detail.png"), full_page=True
    )
    assert not errors
    browser.close()
data["browser"] = {
    "result": "passed",
    "paths": [
        "API history14 rows",
        "new PR14 run detail",
        "Evidence",
        "direct path refresh",
    ],
    "pageErrors": errors,
}
(root / "docs/backend/evidence/new-pr-run.json").write_text(
    json.dumps(data, indent=2) + "\n"
)
print("New actual PR artifact visible in React; direct detail refresh passed")

"""Actual API + persisted PostgreSQL history. No credential value is recorded."""

import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[2]
private = root / ".local/server"
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8090/dashboard")
    expect(page.get_by_role("heading", name="서버 이력 로그인")).to_be_visible()
    page.get_by_label("사용자 이름").fill("validation-admin")
    page.get_by_label("비밀번호").fill((private / "test_admin_password").read_text())
    page.get_by_role("button", name="로그인", exact=True).click()
    expect(page.locator("header .source")).to_have_text("API RESULTS")
    expect(page.locator("tbody tr")).to_have_count(13)
    page.get_by_label("서버 PR 검색").fill("S01")
    expect(page.locator("tbody tr")).to_have_count(2)
    page.get_by_label("서버 상태 필터").select_option("passed")
    expect(page.get_by_text("저장된 분석 결과가 없습니다.")).to_be_visible()
    page.get_by_label("서버 상태 필터").select_option("all")
    page.get_by_label("서버 PR 검색").fill("")
    expect(page.locator("tbody tr")).to_have_count(13)
    page.reload()
    expect(page.locator("tbody tr")).to_have_count(13)
    out = root / "artifacts/phase3"
    out.mkdir(exist_ok=True)
    page.screenshot(path=str(out / "api-history.png"), full_page=True)
    page.locator("tbody a").filter(has_text="D21").first.click()
    expect(page.get_by_role("button", name="기존 결과 재수집")).to_be_enabled()
    page.get_by_role("tab", name="Evidence", exact=True).click()
    expect(page.get_by_role("heading", name="요구사항과 판정 근거")).to_be_visible()
    page.get_by_role("button", name="기존 결과 재수집").click()
    page.get_by_role("link", name="재수집 작업 보기 ↗").click()
    subprocess.run(
        [sys.executable, str(root / "scripts/validation/dispatch_once.py")],
        check=True,
    )
    page.get_by_role("button", name="상태 확인").click()
    page.wait_for_timeout(2500)
    page.get_by_role("button", name="상태 확인").click()
    expect(page.locator(".badge").get_by_text("succeeded", exact=True)).to_be_visible(
        timeout=30000
    )
    page.screenshot(path=str(out / "api-job.png"), full_page=True)
    page.reload()
    expect(page.locator(".badge").get_by_text("succeeded", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.get_by_role("link", name="⇅　Data import").click()
    page.get_by_role("button", name="JSON Import / 데모 모드로 전환").click()
    expect(page.locator("header .source")).to_have_text("DEMO DATA")
    assert not errors, errors
    assert page.evaluate("Object.keys(localStorage).length") == 0
    browser.close()
(out / "browser-results.json").write_text(
    json.dumps(
        {
            "result": "passed",
            "flows": [
                "login",
                "API source",
                "persisted refresh",
                "search",
                "filter",
                "detail",
                "resync queue",
                "job refresh",
                "mobile",
                "explicit demo return",
            ],
            "pageErrors": errors,
        }
    )
)
print("Actual API browser path passed; no credentials/results in localStorage")

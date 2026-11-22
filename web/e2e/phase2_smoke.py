"""Import v1 and v2, inspect independent requirement/usage states."""
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 960})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://localhost:5173/data')
    expect(page.get_by_label('JSON 파일 선택')).to_be_visible()
    page.get_by_label('JSON 파일 선택').set_input_files(str(root/'docs/phase2/example-v2/report.json'))
    expect(page.locator('header .source')).to_have_text('IMPORTED RESULTS')
    page.get_by_role('link', name='▦　Pull requests').click()
    expect(page.get_by_role('row')).to_have_count(2)
    page.get_by_role('link', name='Local fixture — not a GitHub execution').click()
    page.get_by_role('tab', name='Evidence', exact=True).click()
    expect(page.get_by_role('heading', name='요구사항과 판정 근거')).to_be_visible()
    expect(page.get_by_text('REQ-ZERO · 충족 (명시 계약 범위)')).to_be_visible()
    expect(page.get_by_text('호출 0 · 입력 토큰 미측정 · 출력 토큰 미측정 · 비용 미측정')).to_be_visible()
    out = root/'artifacts/phase2';out.mkdir(exist_ok=True, parents=True)
    page.screenshot(path=str(out/'evidence-desktop.png'), full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path=str(out/'evidence-mobile.png'), full_page=True)
    page.get_by_role('link', name='⇅　Data import').click()
    page.get_by_label('JSON 파일 선택').set_input_files(str(root/'docs/report-example.json'))
    expect(page.locator('header .source')).to_have_text('IMPORTED RESULTS')
    page.get_by_role('link', name='▦　Pull requests').click()
    expect(page.get_by_role('row')).to_have_count(13)
    assert not errors, errors
    browser.close()
print('v1/v2 browser import, evidence, null usage, mobile, legacy return: passed')

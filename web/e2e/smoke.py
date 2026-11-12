"""Run with Python Playwright installed and Vite on port 5173."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

repo = Path(__file__).resolve().parents[2]
out = repo / 'artifacts/react-e2e'
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 960},
                                  permissions=['clipboard-read', 'clipboard-write'],
                                  record_video_dir=str(out))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost:5173/dashboard')
    expect(page.get_by_role('row')).to_have_count(13)
    page.screenshot(path=str(out / 'dashboard.png'), full_page=True)
    page.get_by_label('PR 검색').fill('S01')
    expect(page.get_by_role('row')).to_have_count(3)
    page.get_by_label('상태 필터').select_option('passed')
    expect(page.get_by_text('검색 결과가 없습니다.')).to_be_visible()
    page.get_by_label('상태 필터').select_option('all')
    page.get_by_label('정렬').select_option('reviews')
    page.get_by_role('link', name='⇅　Data import').click()
    upload = page.get_by_label('JSON 파일 선택')
    upload.set_input_files({'name': 'bad.json', 'mimeType': 'application/json', 'buffer': b'{"schemaVersion":"99"}'})
    expect(page.get_by_role('alert')).to_be_visible()
    upload.set_input_files(str(repo / 'docs/report-example.json'))
    expect(page.locator('header .source')).to_have_text('IMPORTED RESULTS')
    page.goto('http://localhost:5173/dashboard')
    # Refresh intentionally restores demo, so import again before detail navigation.
    page.get_by_role('link', name='⇅　Data import').click()
    page.get_by_label('JSON 파일 선택').set_input_files(str(repo / 'docs/report-example.json'))
    expect(page.locator('header .source')).to_have_text('IMPORTED RESULTS')
    page.get_by_role('link', name='▦　Pull requests').click()
    page.get_by_role('link', name='S01-buggy · 시드 계약 평가').click()
    expect(page.get_by_role('heading', name='S01-buggy · 시드 계약 평가')).to_be_visible()
    page.get_by_role('tab', name='AI Review', exact=True).click()
    expect(page.get_by_role('link', name='커밋의 코드 위치 ↗')).to_have_attribute('href', __import__('re').compile(r'https://github.com/solw29/teamsync-ai/blob/[0-9a-f]{40}/demo_s01.py#L6'))
    page.get_by_role('tab', name='Tests', exact=True).click()
    page.get_by_role('button', name='코드 복사').first.click()
    expect(page.get_by_role('status')).to_have_text('코드를 복사했습니다.')
    assert 'from demo_s01 import' in page.evaluate('navigator.clipboard.readText()')
    page.screenshot(path=str(out / 'tests.png'), full_page=True)
    page.get_by_role('tab', name='Execution', exact=True).click()
    expect(page.get_by_role('link', name='GitHub Actions 실행 ↗')).to_be_visible()
    page.get_by_role('link', name='▤　Evaluation').click()
    expect(page.get_by_role('heading', name='Evaluation', exact=True)).to_be_visible()
    page.screenshot(path=str(out / 'evaluation.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('link', name='⇅　Data import').click()
    page.keyboard.press('Tab')
    page.screenshot(path=str(out / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.get_by_role('button', name='데모 데이터로 초기화').click()
    expect(page.locator('header .source')).to_have_text('DEMO DATA')
    page.get_by_label('JSON 파일 선택').set_input_files({'name': 'empty.json', 'mimeType': 'application/json',
        'buffer': b'{"schemaVersion":"1.0","analyses":[],"evaluation":null}'})
    expect(page.locator('header .source')).to_have_text('IMPORTED RESULTS')
    page.get_by_role('link', name='▦　Pull requests').click()
    expect(page.get_by_text('분석 결과가 없습니다. Data에서 결과 파일을 가져오세요.')).to_be_visible()
    page.route('**/demo.json', lambda route: route.fulfill(status=500, body='unavailable'))
    page.reload()
    expect(page.get_by_role('alert')).to_be_visible()
    page.unroute('**/demo.json')
    page.get_by_role('button', name='데모 다시 불러오기').click()
    expect(page.get_by_role('row')).to_have_count(13)
    assert not errors, errors
    context.close()
    browser.close()
(out / 'results.json').write_text(json.dumps({'result': 'passed', 'pageErrors': errors,
    'flows': ['load', 'search', 'filter', 'sort', 'invalid import', 'actual D10 import',
              'detail tabs', 'commit link', 'clipboard', 'evaluation', 'mobile', 'demo reset']}))
print('Browser smoke passed: 12 flows, no page errors')

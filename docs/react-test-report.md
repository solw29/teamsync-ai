# React 확장 검증 — 2026-11-12 (KST)

## 현재 결과

- Python: 기존 회귀와 Exporter 테스트 포함 27개 통과, Ruff 통과.
- TypeScript 타입 검사 및 Vite production 빌드 통과.
- Vitest: 6개 통과. 실제 익명화 데이터, 버전/누락/위험 URL/중복 ID 거부, 목록 검색·정렬·빈 상태를 검증.
- Chromium Playwright: 실제 D10 import, 잘못된 JSON 거부, 검색·상태 필터·정렬 조작, 상세 탭, SHA 고정 코드 링크, 실제 clipboard, 평가 화면, 모바일 overflow, 데모 복귀, 빈 데이터, 데모 HTTP 500 후 재시도 흐름 통과.
- 페이지 JS 오류 없음. 모바일 390×844에서 문서 가로 overflow 없음.
- [Dashboard 캡처](images/react-dashboard.png), [모바일 캡처](images/react-mobile.png), [브라우저 시연 녹화](react-demo.mp4).

브라우저 녹화는 익명화한 실제 데이터로 화면을 탐색한 자동 시연이며 사람 발표나 배포 환경의 접속 영상이 아닙니다. 키보드 Tab 이동과 focus 스타일은 기본 확인만 했으며 전체 접근성 표준 준수를 인증하지 않습니다. 로딩 상태는 구현했고 오류·재시도를 실행했습니다. 모든 조합의 데이터/브라우저를 테스트한 것은 아닙니다.

## 재현

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
cd web
npm ci
npm test
npm run build
npm run dev -- --port 5173
# 별도 터미널: Python playwright 및 Chromium/FFmpeg가 설치된 환경에서
# python web/e2e/smoke.py (저장소 루트)
```

E2E는 시스템 `/usr/bin/chromium`을 사용합니다. 클라우드의 Playwright FFmpeg 위치를 사용할 때는 `PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright`를 지정합니다.

## 완료 범위와 남은 작업

D11~D19의 읽기 전용 로컬 구현·검증과 D20의 빌드·문서·녹화·정적 배포 설정을 준비했습니다. 배포된 SPA URL은 아직 없습니다. Vercel 계정 연결/배포 대상 결정과 실제 외부 URL의 검증이 필요합니다. 환경 Publish는 수행하지 않았습니다.

원래 파이프라인의 분석/생성 테스트/댓글/Discord 실행 동작은 바꾸지 않았습니다. 별도 dashboard workflow가 보존된 D10 evidence를 변환해 import JSON과 빌드를 artifact로 남깁니다. 실시간 PR의 원시 잡 artifact를 자동 수집하는 서버/API 연동은 이번 버전에 없습니다.

D10에 없는 원래 PR 제목·세부 단계 시간·실패 이유는 만들지 않습니다. UI의 제목은 사례 ID이고 duration은 실행 생성~댓글 시간입니다. 6쌍의 집계와 PR별 상세를 표시하지만 개별 초안의 버그/수정 쌍 판정 상세는 원본 D6 evidence 보고서를 함께 확인해야 합니다. 사용자가 지적 내용을 판정·편집해 저장하는 기능은 추가하지 않았습니다.

## GitHub Actions 검증

소스 커밋 `c0a49e9`에서 [Dashboard build and report export #43151017817](https://github.com/solw29/teamsync-ai/actions/runs/43151017817)와 [기존 TeamSync CI #43151017757](https://github.com/solw29/teamsync-ai/actions/runs/43151017757)가 성공했습니다. `npm ci`부터 테스트·타입 검사·빌드·Exporter·두 artifact 업로드까지 실제 runner에서 실행됐습니다. 생성된 `dashboard-import-report` artifact를 내려받아 Chromium에서 가져오고 12개 PR 표시를 확인했습니다. 정적 빌드 artifact 생성은 웹 호스팅 배포를 의미하지 않습니다.

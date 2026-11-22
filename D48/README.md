# D48 — React API 연동과 데이터 출처

DOCX 3-08 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

demo/import/api DataSource와 로그인·서버 목록/상세/통계·작업 화면을 추가한다.

## 완료 기준과 실제 확인

새로고침·직접 경로·검색/필터·상세 Evidence·재수집·모바일을 검증하고 API 실패 시 데모로 자동 전환하지 않는다.

[실제 브라우저](../docs/backend/evidence/browser-results.json), `web/e2e/backend_smoke.py`; APIclient401/계약과 hidden/inactive polling 중지 unit tests. 자동 polling은 실시간 보장이 아니다.

## 어떤 기능을 어떻게 구현했는가

`web/src/api/`, `data/source.ts`에서 include cookie+CSRF 요청과 Zod 응답 검증을 수행한다. API 결과는 DB에 남고 sessionStorage에는 source flag만 저장한다. AbortController와 generation으로 이전 응답을 막고 visible+진행 중 작업에만 10초 polling한다.

## 다른 방법과 선택 근거

localStorage 결과 저장은 서버 권한/이력과 충돌하고 서버 장애를 숨길 수 있다. 명시적 출처 전환과 서버 이력 조회를 선택했다. WebSocket보다 제한 polling이 로컬 단일 관리자 환경의 운영 부담이 작다.

## 개발 중 문제와 해결·남은 한계

재수집 응답과 분석 결과의 상태를 혼동하지 않도록 job 전용 화면을 만들었다. API 모드 새로고침 때 demo로 돌아가는 문제는 비밀 없는 source preference만 저장해 해결했다. legacy null 계약도 보완했다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

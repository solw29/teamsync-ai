# D46 — 상태 대조와 재처리 API

DOCX 3-06 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

resync202·취소·작업 이력과 주기 overlap scan을 추가한다.

## 완료 기준과 실제 확인

중복 클릭은 idempotency key로 같은 작업을 반환하고 retry/최종 사유를 조회할 수 있어야 한다. 재수집은 LLM 호출·Actions 재실행을 유발하지 않는다.

retry-after·cancel·delivery recovery 테스트와 실제 `queued→running→retrying→running→succeeded` 이력. 자동 스캔은 60초 주기이며 즉시 수집 보장이 아니다.

## 어떤 기능을 어떻게 구현했는가

수집 cursor는 scan 시각과 실제 저장 성공 시각을 분리한다. 10분 overlap과 3페이지 상한으로 완료된 pull_request 결과를 탐색한다. jobs의 상태·event 이력과 GitHub/analysis/collection 상태는 별도다. React에서 작업 이력과 개별 상태를 표시한다.

## 다른 방법과 선택 근거

workflow rerun은 분석 비용과 코드 실행을 다시 발생시킨다. 이미 생성된 artifact를 pull하는 재수집만 제공한다. overlap은 스캔 경계 누락에 대응하며 무제한 API 탐색 대신 상한 오류를 명시한다.

## 개발 중 문제와 해결·남은 한계

credential이 없을 때 초기 client 생성이 실패하면 scan 오류가 표시되지 않던 경로를 수정해 SyncCursor.last_error에 남긴다. 오래된 worker는 lease token 비교로 최신 작업을 덮지 못한다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

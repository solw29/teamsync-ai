# 11월 7일 · D6 — 시드 PR 쌍 평가·프롬프트 개선·측정표

일정 기준: 상세계획 C(1인·10일). 구조·보안 참고: 상세계획 G. 날짜는 계획상의 일정이며 실제 완료일이 아닙니다.

## 구현/준비한 내용

D1의 S01~S06 계약에 대응하는 버그/수정 쌍과 오프라인 평가기를 구현했습니다. 네 가지 통과/실패 조합을 분류하고 환경 오류는 별도로 표시합니다. 결과 출처는 handwritten_contract_not_llm입니다.

관련 파일: `teamsync/evaluate.py, tests/unit/test_evaluate.py, evaluation.csv`.

## 확인 방법

저장소 루트에서 `ruff check .`, `pytest -q`를 실행합니다. D6 오프라인 계약 검증은 `python -m teamsync.evaluate`로 실행합니다. 로컬 검증과 GitHub 실서비스 검증은 구분합니다.

## 당시 남은 완료 조건 (아래 최신 기록으로 갱신)

실제 6쌍 PR에서 모델 리뷰·초안을 수집하고 evaluation.csv를 작성합니다. 버그 지적률·수정 PR 오탐·위치 유효율·실행 가능률·버그 검출률·댓글 지연 중앙값/최댓값을 측정합니다. 미측정 값을 0으로 채우지 않습니다. 필수 연동 미검증이므로 일정 조율은 보류합니다.

## 이번 로컬 검증 결과

`offline-results.json`: 수기 계약 테스트 6쌍 모두 버그 버전 실패·수정 버전 통과. LLM 생성 테스트나 실제 PR 평가 결과가 아닙니다. 전체 회귀 테스트 24개와 Ruff가 통과했습니다.

## 2026-11-12 실서비스 검증 갱신

실제 PR 6쌍 평가를 완료했습니다. evaluation.csv와 live-report.md, live-evidence/가 이번 실측 결과입니다. 앞선 offline-results.json은 수기 계약 결과로 유지합니다. 전체 main 회귀 테스트는 현재 25개입니다.

자세한 결과: [D6 실측 보고서](../1107_D6/live-report.md).

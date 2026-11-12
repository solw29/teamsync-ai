# 11월 6일 · D5 — 테스트 초안 생성·격리 잡 실행·상태 표시

일정 기준: 상세계획 C(1인·10일). 구조·보안 참고: 상세계획 G. 날짜는 계획상의 일정이며 실제 완료일이 아닙니다.

## 구현/준비한 내용

최대 5개 초안을 임시 파일로 실행하고 passed/failed/environment_error/not_run을 구분합니다. 별도 폐기형 runner, 시크릿 미전달, checkout 인증 미보존, 테스트 30초·잡 5분 제한을 적용합니다. 자동 커밋하지 않습니다.

관련 파일: `teamsync/schema.py, run_generated_tests.py, github_comments.py, .github/workflows/teamsync.yml`.

## 확인 방법

저장소 루트에서 `ruff check .`, `pytest -q`를 실행합니다. D6 오프라인 계약 검증은 `python -m teamsync.evaluate`로 실행합니다. 로컬 검증과 GitHub 실서비스 검증은 구분합니다.

## 당시 남은 완료 조건 (아래 최신 기록으로 갱신)

실제 모델 초안을 Actions에서 실행해 상태 라벨 확인. 로컬 플래그만으로 보안 격리된 것으로 취급하지 않습니다. 통과는 테스트 품질 보증이 아닙니다.

## 2026-11-12 실서비스 검증 갱신

동일 LLM 초안 30개를 실제 CI에서 버그·수정 SHA에 실행했습니다. 6개 초안, 3/6 사례가 버그 실패·수정 통과를 보였습니다. 모든 초안의 품질이 검증된 것은 아닙니다.

자세한 결과: [D6 실측 보고서](../1107_D6/live-report.md).

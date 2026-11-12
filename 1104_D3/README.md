# 11월 4일 · D3 — diff 수집·필터링·줄 번호, LLM 리뷰 JSON

일정 기준: 상세계획 C(1인·10일). 구조·보안 참고: 상세계획 G. 날짜는 계획상의 일정이며 실제 완료일이 아닙니다.

## 구현/준비한 내용

추가 줄만 수집하고 lock·생성 파일을 제외합니다. 300줄/약 24,000자 상한과 생략 표시, 엄격한 Pydantic 스키마, API 타임아웃·키 누락 상태를 구현했습니다.

관련 파일: `teamsync/collect_diff.py, analyze.py, schema.py, prompts/review.txt`.

## 확인 방법

저장소 루트에서 `ruff check .`, `pytest -q`를 실행합니다. D6 오프라인 계약 검증은 `python -m teamsync.evaluate`로 실행합니다. 로컬 검증과 GitHub 실서비스 검증은 구분합니다.

## 당시 남은 완료 조건 (아래 최신 기록으로 갱신)

실제 API 키로 소형 PR의 리뷰 JSON 생성 확인. 모델·사용량·응답 시간을 기록합니다.

## 2026-11-12 실서비스 검증 갱신

실제 PR 12개에서 분석 JSON 생성에 성공했습니다. import 누락 보완 후의 결과를 D6 실측 보고서에 보존했습니다.

자세한 결과: [D6 실측 보고서](../1107_D6/live-report.md).

# 11월 5일 · D4 — 근거 검증·부분 게시·Discord·첫 end-to-end

일정 기준: 상세계획 C(1인·10일). 구조·보안 참고: 상세계획 G. 날짜는 계획상의 일정이며 실제 완료일이 아닙니다.

## 구현/준비한 내용

diff의 실제 추가 파일·줄만 게시합니다. 무효 지적 제외 건수, 봇 마커 댓글 생성/갱신, AI 이전 검사 결과 게시, 최종 Discord 전송을 구현했습니다.

관련 파일: `teamsync/validate_findings.py, github_comments.py, discord_notify.py, .github/workflows/teamsync.yml`.

## 확인 방법

저장소 루트에서 `ruff check .`, `pytest -q`를 실행합니다. D6 오프라인 계약 검증은 `python -m teamsync.evaluate`로 실행합니다. 로컬 검증과 GitHub 실서비스 검증은 구분합니다.

## 당시 남은 완료 조건 (아래 최신 기록으로 갱신)

실제 같은 저장소 PR에서 댓글 1개 갱신·Discord 수신·LLM 오류 시 부분 게시 확인. 1차 end-to-end 실측은 아직 수행하지 않았습니다.

## 2026-11-12 실서비스 검증 갱신

실제 PR 12개에서 최종 게시와 Discord HTTP 성공을 확인했습니다. 위치 15/15, 마커 댓글 중복 0건입니다. Discord 채널 화면은 미확인입니다.

자세한 결과: [D6 실측 보고서](../1107_D6/live-report.md).

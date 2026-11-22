# D49 — 운영 로그와 저장 정책

DOCX 3-09 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

상관 ID·큐 대기/수집 시간·작업 지표·보존/삭제/감사와 실제 백업 복원을 추가한다.

## 완료 기준과 실제 확인

로그에 원문·비밀번호·키를 넣지 않고 DB/cache 장애 및 삭제 후 통계, 백업 복원 행 수 일치를 확인한다.

[실제 dump/restore](../docs/backend/evidence/backup-restore.json). dump는 0600·gitignore이며 공개하지 않는다. artifact 만료는 GitHub 원본에만 영향을 주며 DB 결과 삭제와 다르다. 복원 운영 시 기존 세션을 폐기해야 한다.

## 어떤 기능을 어떻게 구현했는가

`telemetry.py` allowlist와 API request ID를 연결한다. diagnostics는 소유자의 jobs 상태별 수와 failed/(failed+succeeded)를 반환하며 분모0은 null이다. 90일 보존 정리는 인증+CSRF 관리 API로 명시적으로 실행한다. run 삭제는 자식 cascade와 stats_version 변경을 적용한다.

## 다른 방법과 선택 근거

모든 요청 body/exception dump는 원문 코드·secret 노출 위험이 있다. 구조화된 제한 필드와 안전한 사유 code를 선택했다. 백업은 DB만 포함하며 외부 credential 파일은 별도 보관한다.

## 개발 중 문제와 해결·남은 한계

Compose bind secret의 UID 문제와 TLS 프록시 CA 문제가 있었다. 권한 변경 대신 privilege drop, 검증 환경에서는 BuildKit CA secret으로 신뢰 체인을 추가했다. TLS 검증을 끄지 않았다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

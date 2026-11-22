# D41 — 서버 책임과 기본 접근 통제

DOCX 3-01 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

FastAPI·로컬 단일 관리자·세션·CSRF·Compose를 추가한다. 분석과 테스트 실행 주체는 기존 Actions로 유지한다.

## 완료 기준과 실제 확인

인증/세션 만료/CSRF/Origin 차단과 설정 누락을 시험하고 DB·Redis의 기본 호스트 포트 공개를 없앤다.

`test_auth_origin_csrf_and_logout`, `test_session_expiry_and_sensitive_logs`, `test_missing_config_is_explicit`; Docker 검증은 통합 검수 문서 참조.

## 어떤 기능을 어떻게 구현했는가

`server/app/main.py`, `security.py`, `config.py`, `compose.dev.yaml`에서 첫 초기화는 singleton PK와 무작위 bootstrap token으로 보호한다. 비밀번호는 salted scrypt, 세션과 CSRF는 해시로 DB에 저장한다. HttpOnly/SameSite=Strict 쿠키와 저장소 소유권 검사를 적용한다.

## 다른 방법과 선택 근거

JWT는 폐기·회수 처리가 추가되고 외부 OAuth는 초기 설치 의존성이 늘어난다. 단일 관리자 로컬 설치에서 서버 세션이 만료·로그아웃·관리자 제어를 단순하게 한다. 원격 공개와 다중 역할은 이번 범위에 포함되지 않는다.

## 개발 중 문제와 해결·남은 한계

Compose의 0600 파일 secret을 nonroot 앱이 읽지 못했다. 파일 권한을 넓히지 않고 entrypoint가 필요한 값만 읽은 뒤 uid/gid 65534로 영구 전환한다. 값은 argv·로그에 넣지 않는다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

# D42 — PostgreSQL 모델과 보고서 저장

DOCX 3-02 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

repositories/PR/runs와 정규화된 stage/finding/requirement/evidence/usage, Alembic migration을 추가한다.

## 완료 기준과 실제 확인

보존 v1 12건과 실제 v2 저장, 중복 멱등성, attempt 보존, 중간 rollback, migration 및 DB 재시작을 검증한다.

실제 13건 저장·DB 재시작 보존, `test_real_concurrent_distinct_attempts_and_duplicates`, `test_v2_rollback_and_distinct_attempts`; backup-restore.json.

## 어떤 기능을 어떻게 구현했는가

`models.py`와 `storage.py`에서 repository ID·run ID·attempt 유일 제약, nested savepoint와 외부 transaction을 사용한다. GH 숫자 ID는 BigInteger다. v1의 알 수 없는 attempt는 0으로 저장하고 API에서는 null로 표현한다. raw 보고서와 정규화 행을 함께 저장하고 latest/latestSuccessful을 구분한다.

## 다른 방법과 선택 근거

JSON 파일만 저장하면 동시 갱신·권한·페이지네이션이 어렵다. JSONB만 사용하는 대안보다 자식 테이블을 두어 관계·집계를 보장하되 원문도 보존해 추적 가능하게 했다. SQLite 단위 테스트만으로 PG 동시성을 보장하지 않아 실제 PostgreSQL 검사도 추가했다.

## 개발 중 문제와 해결·남은 한계

동시 최초 PR 생성과 동일 실행 저장 경쟁이 발생할 수 있어 유일 제약과 savepoint 뒤 재조회로 처리했다. Pydantic 기본값 직렬화가 원문 checksum을 바꾸는 문제는 다운로드 원문 hash/payload를 보존해 해결했다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

# D45 — Celery 작업 큐와 유실 복구

DOCX 3-05 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

DB jobs/outbox, Redis broker, Celery worker와 lease 복구를 추가한다.

## 완료 기준과 실제 확인

202 뒤 broker가 중단돼도 outbox가 남고, 전송 후 crash·중복·worker 종료 후 동일 결과가 중복 저장되지 않아야 한다.

[실제 큐](../docs/backend/evidence/queue-smoke.json), [SIGKILL 복구](../docs/backend/evidence/worker-recovery.json), outbox crash/duplicate unit tests. SIGKILL 시험은 격리된 solo validation task로 claim 후 중단했으며 prefork 자식 종료 시험은 아니다.

## 어떤 기능을 어떻게 구현했는가

`jobs.py`, `worker.py`에서 요청과 outbox를 한 transaction에 저장한다. dispatcher는 전송 후 sent를 기록하고 worker는 job ID만 받는다. row lock·lease token CAS·유일키·late ack·제한 재시도를 사용한다. 오래된 running과 전송됐지만 claim되지 않은 작업도 재발행한다.

## 다른 방법과 선택 근거

FastAPI BackgroundTasks는 프로세스 종료 시 유실되고 Redis 메시지만으로는 DB commit/발행 사이 원자성을 보장하지 못한다. transactional outbox+at-least-once 전달과 멱등 저장을 선택했다. 외부 알림 exactly-once는 주장하지 않으며 알림은 기존 Actions가 담당한다.

## 개발 중 문제와 해결·남은 한계

전송 후 dispatcher rollback은 중복 메시지를 만들 수 있다. 중복 claim을 차단하고 immutable run 유일키를 최종 경계로 둔다. broker 중단 때 send 자체의 긴 재시도를 끄고 DB backoff로 통일했다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

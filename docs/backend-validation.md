# 3차 백엔드 통합 검수 — 2026-11-23 KST

## 작업·완료 기준과 현재 증거

D41~D50은 DOCX3-01~3-10에 대응한다. 작업은 영속 API·안전한 GitHub pull·내구성 큐·React 연결과 복구 검증이며, 각 단계의 판단 근거와 문제 해결은 해당 README에 기록했다. 환경은 Python3.12, PostgreSQL17.5, 별도 Redis7.4.4 broker/cache, Node24, Chromium이다. 표준 Compose는 DB/Redis를 호스트에 노출하지 않는다. 검증 프로젝트만 loopback55432/56379/56380 override를 사용했다.

- 기존 Python 테스트 **59/59** 통과.
- 서버 테스트 **24/24** 통과. 실제 PostgreSQL `_test` DB의 동시 attempt/중복 저장 검사 포함. TEST_DATABASE_URL 없이 실행하면23통과/1skip이며 이를24통과로 세지 않는다.
- React **13/13** 통과, TypeScript·Vite build 통과. Python 응답 모델에서 생성한 fixture를 React Zod로 검증한다.
- Ruff 전체 검사 통과. Starlette TestClient의 httpx deprecation 경고1개는 남아 있다.
- 실제12개 보존 결과+GitHub v2 run **45015243674 attempt1**을 PG에 저장해 **13행** 조회. 이는 신규 run 증거와 구분한다.
- 실제 HTTP202→DB outbox→Redis→Celery→GitHub artifact→PG→API 경로 성공. 브라우저10가지 흐름 통과, page error0.
- cache/broker/DB/worker 장애·복구 **4/4** 실제 주입 성공. 아래 범위와 조건을 따른다.
- 실제 pg_dump→별도 DB pg_restore 주요5테이블 행 수 일치. 운영 DB 전환은 수행하지 않았다.

[실제 수집](backend/evidence/live-import.json) · [실제 큐](backend/evidence/queue-smoke.json) · [브라우저](backend/evidence/browser-results.json) · [복원](backend/evidence/backup-restore.json)

## 장애 주입 결과와 해결

| 중단 대상 | 관측 결과 | 복구 결과 |
| --- | --- | --- |
| cache Redis | 통계HTTP200, database_fallback; broker ready | 별도 cache 재시작 후 사용 가능 |
| broker Redis | 요청202 유지, outbox 미전송/시도1 저장 | Redis 재시작 후 dispatch→succeeded |
| PostgreSQL | readiness503 | 재시작 후 readiness200,13행 유지 |
| worker | 격리 solo Celery validation task가 production claim 후 SIGKILL | lease3초 만료→reconcile→정상 production task로 재수집, attempts2/succeeded |

[cache/broker/DB 증거](backend/evidence/faults-performance.json) · [worker 증거](backend/evidence/worker-recovery.json)

worker 시험은 검증용 격리 task로 claim 후 fetch/save 전에 강제 종료했다. prefork 자식 kill, 전체 호스트 전원 차단, Celery hard time limit의 모든 조합을 검증한 것은 아니다. DB 저장 전 enqueue 유실·전송 직후 dispatcher rollback·중복 전달은 서버 자동 테스트로 별도 검사한다. 외부 알림 exactly-once는 주장하지 않는다.

## 같은 조건의 성능 측정

실제13행 저장소 통계, 각100회, 같은 프로세스·DB·네트워크, warm 상태:

| 경로 | p50 ms | p95 ms | SQL문/100회 |
| --- | ---: | ---: | ---: |
| DB 직접 | 1.566 | 2.086 | 200 |
| warm cache | 1.233 | 2.834 | 100 |

warm cache 측정은100회 모두 hit였다. 매 요청 DB version 확인1회가 남는다. p50/SQL은 감소했지만 p95는 증가했다. 작은 표본에서 cache가 항상 빠르다고 해석하지 않는다. cache TTL30초, 요청 시작 후 동시 commit 이전 snapshot 허용, 직접 SQL 갱신은 지원 경계를 벗어난다.

인덱스 측정은 사용자 트래픽이 아닌 **합성10만행/100개 저장소**, 전용 teamsync_test 임시 테이블에서 동일 WHERE/ORDER BY/LIMIT20을 각30회 수행했다. 실행 계획·buffer·p50/p95 원문은 [index-measurement.json](backend/evidence/index-measurement.json)에 있다. 실제 운영 DB 인덱스를 삭제하지 않았으며 테스트 테이블은 측정 후 제거했다.

## 구현 방식·판단 근거·운영 제한

단순 background task 대신 DB outbox로 접수 내구성을 보장하고 at-least-once 전달+멱등 저장으로 복구한다. Webhook 대신 outbound pull을 사용해 로컬 수신 포트와 PR 코드 실행을 요구하지 않는다. 캐시는 통계 하나로 한정해 version 키·TTL·권한 검사·DB fallback을 검증했다. 모든 raw 원문은 결과 저장 대상일 수 있지만 운영 로그에는 남기지 않는다. 비용 정보가 없으면 usage null을 유지한다.

실제 수집 검증은 기존 GH_TOKEN binding을 사용하는 호스트 worker에서 수행했다. token 값은 기록·복사·게시하지 않았다. 기본 Compose에는 credential이 없으며 운영 시 별도의 repo 제한 Actions-read 파일 secret을 연결해야 한다. 로컬 환경에서 원격 TLS·다중 사용자 권한과 4/5차 배포 제품을 완료한 것으로 표시하지 않는다.

세부 실행·백업·credential 주입 방법과 재현 조건은 [운영 가이드](backend/README.md). 확인 중 발생한 UID/CA/checksum/null/경쟁 조건 문제와 해결은 D41~D50 README에 각각 연결했다.

컨테이너 빌드 성공, migration one-shot 종료0, API readiness200와 `/proc/1/status` UID65534를 확인했다. 해당 컨테이너가 제공하는 production React에서 브라우저 smoke도 다시 통과했다. `docker exec`의 새 관리 프로세스 기본 UID와 API PID1의 UID는 구분해서 확인했다.

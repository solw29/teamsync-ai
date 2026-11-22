# TeamSync 결과 서버 운영 가이드

DOCX 3-01~3-10 구현. 기록 폴더는 사용자 지정에 따라 D41~D50이다. 로컬 단일 관리자 설치가 기본이며 분석·테스트·Discord 알림은 기존 Actions가 담당한다. 서버는 PR 코드를 실행하지 않고 기존 report artifact만 읽는다.

## 작업과 완료 기준

작업은 결과 영속 저장, 인증된 API, GitHub pull, 내구성 큐, React 연결, 캐시·운영 복구다. 완료 기준과 실제 검증·제한은 [통합 검수](../backend-validation.md), 상세 판단은 [D41](../../D41/README.md)~[D50](../../D50/README.md)에 있다. 4차 설치 배포 묶음과 5차 역할·wizard 고도화는 포함하지 않는다.

## 로컬 시작

필요 환경: Docker Compose v2, 인터넷 접근. 표준 Docker 빌드는 Python3.12와 Node24를 사용한다.

```bash
python scripts/server-init.py
docker compose -f compose.dev.yaml build
docker compose -f compose.dev.yaml up -d
curl --fail http://127.0.0.1:8090/ready
```

`http://127.0.0.1:8090/dashboard`에서 첫 관리자 초기화와 로그인을 진행한다. 초기화 토큰은 `.local/server/bootstrap_token`의 값을 로컬에서 확인해 입력한다. 토큰·비밀번호를 이슈·스크린샷·공유 터미널 기록에 붙이지 않는다. 재시작은 파일이나 DB를 초기화하지 않는다. 이미 초기화한 설치는 bootstrap이 닫힌다. `down -v`는 데이터를 삭제하므로 일반 종료에는 `docker compose ... stop`을 사용한다.

DB·broker·cache는 내부 네트워크만 사용하고 API만 loopback8090에 바인딩한다. `/health`는 프로세스 생존, `/ready`는 DB 접근을 확인한다. bootstrap은 API 컨테이너에만 마운트한다. entrypoint는 파일 secret을 읽고 uid/gid65534로 전환하며 이후 명령은 root로 실행하지 않는다. DB 비밀번호는 `.local`0600 파일과 필요한 프로세스 환경에 존재한다. 컨테이너 관리자/호스트 관리자에게 숨겨지는 secret vault는 아니다.

## GitHub 읽기 credential 연결

기본 Compose에는 GitHub 토큰이 없어서 조회·Import는 가능하지만 pull 수집은 `github_credential_missing`으로 끝난다. 해당 저장소에 한정된 fine-grained token의 Actions read와 metadata read만 부여하고, 개인 로컬 파일 `.local/server/github_read_token`에0600으로 보관한다. Actions Secrets는 서버 컨테이너로 자동 전달되지 않는다. 토큰을 React·DB·Redis 메시지·Git에 넣지 않는다.

별도 로컬 override를 만들어 **worker와 scheduler**에만 다음 secret을 추가한다. API에는 필요하지 않다.

```yaml
services:
  worker:
    secrets: [db_password, github_read_token]
  scheduler:
    secrets: [db_password, github_read_token]
secrets:
  github_read_token:
    file: .local/server/github_read_token
```

```bash
docker compose -f compose.dev.yaml -f .local/github.override.yaml up -d worker scheduler
```

서버는 API의 실제 repository ID·workflow ID와 report manifest를 대조한다. UI 연결 설정에서 repository ID, owner/repository, 허용 workflow ID를 등록한다. 이름만으로 권한을 부여하지 않는다. 재수집은 기존 결과 다운로드이며 workflow rerun이나 LLM 호출이 아니다. credential 권한의 최소성은 운영자가 GitHub에서 확인해야 한다.

## 구현과 선택 근거

PostgreSQL은 유일키·관계·transaction으로 결과와 jobs/outbox를 보관한다. DB outbox→Redis broker→Celery는 적어도 한 번 전달하며 lease+CAS+run 유일키로 중복 저장을 막는다. DB 저장과 Redis publish 사이 유실을 방지하려고 단순 BackgroundTasks 대신 outbox를 사용했다. scheduler는2초마다 전달·복구,60초마다10분 overlap으로 완료 run을 조회한다. 페이지 상한 초과는 오류로 표시하고 cursor를 진행시키지 않는다.

별도 cache Redis는 통계만30초 TTL로 보관한다. 권한을 확인한 뒤 DB stats_version을 읽고 키에 포함하므로 commit 후 이전 버전 키를 사용하지 않는다. 이미 시작한 조회는 동시에 진행되는 쓰기 이전의 snapshot을 볼 수 있다. API 외부에서 SQL로 데이터를 바꾸면 version이 갱신되지 않으므로 운영 수정은 API를 사용한다. cache 장애는 DB fallback, broker 장애는 내구성 작업 대기로 분리한다.

React에는 demo/import/api 출처를 표시한다. API 실패를 demo로 교체하지 않는다. 쿠키 세션은 HttpOnly이며 sessionStorage에는 출처 flag만, 비밀번호·결과·CSRF는 저장하지 않는다. API의 CSRF는 메모리에만 유지한다. 진행 중/visible일 때만10초 polling하므로 실시간 보장은 아니다. 공개 원격 서비스는 TLS·Secure 쿠키·명시적 Origin 환경 구성이 별도로 필요하다. 기본은 localhost 개발용이다.

## API와 오류

현재 OpenAPI는 `/openapi.json`, 스냅샷은 [contract/openapi.json](contract/openapi.json). `runs/detail/stats.json`은 실제 FastAPI 응답으로 생성한 공개 fixture이며 React Zod 테스트가 읽는다. 내부 세션·키는 fixture에 없다.

목록 `/api/runs?repositoryId=...`는 q/status/start/end/sort/limit/cursor를 받는다. 상세 `/api/runs/{id}`, PR별 `/api/repositories/{id}/pulls/{number}/history`, 통계 `/api/repositories/{id}/stats`다. 쓰기에는 세션+X-CSRF-Token이 필요하다. sync/resync는 Idempotency-Key와202 job을 반환한다. `/api/jobs`는 최근100건, `/api/jobs/{id}`는 상태 전환100건과 최종 사유를 표시한다. 과거 전체 감사 검색·장기 job 아카이브는 이번 범위 밖이다.

오류는 `{"error":{"code":"...","requestId":"..."}}`로 통일한다. 401은 재로그인,403은 접근/CSRF/Origin 확인,409는 immutable 보고서 충돌,503은 저장소 장애다. GitHub403은 영구 권한 실패,429/5xx와 아직 도착하지 않은 artifact는 제한 재시도다. artifact 만료·위조·크기 초과는 passed로 바꾸지 않는다.

## 운영 지표와 보존

request 로그는 requestId/status/durationMs, job 로그는 jobId/runId/requestId/attempt/queueWaitMs/durationMs와 안전한 사유만 남긴다. 코드 원문·대화·HTTP body/header·signed URL·credential·DSN은 기록하지 않는다. `/api/diagnostics`의 실패율은 **failed / (failed+succeeded)**이며 취소·대기·진행·재시도는 분모에서 제외한다. 분모0은 null이다. cache hit ratio는 hits/(hits+misses)이고 프로세스 재시작 때 초기화된다. fallback 수는 cache 읽기 실패 횟수다. 운영 DB의 장기 시계열 계측을 구축한 것은 아니다.

사용량이 없는 실행은 usage null이며 비용0으로 단정하지 않는다. `POST /api/retention`은 현재 관리자의 저장 결과 중 collected_at90일 이전을 명시적으로 삭제한다. 자동 파괴적 스케줄은 두지 않았다. `DELETE /api/runs/{id}`는 자식 행을 cascade 삭제하고 통계 버전을 올린다. 감사에는 행위와 대상 ID만 남긴다. jobs/outbox/감사 이력의 별도 장기 정리는 운영 정책이 필요하다. GitHub artifact 만료는 저장된 DB 행의 삭제와 별개다.

## 백업·복원

다음은 기본 project `teamsync-dev` 예시다. dump는 원문 보고서와 사용자·세션 해시를 포함할 수 있어 비공개로 취급하고 암호화된 별도 보관소로 옮긴다. credential 파일은 dump에 포함되지 않는다.

```bash
umask 077
mkdir -p .local/backups
docker compose -f compose.dev.yaml exec -T db pg_dump -U teamsync -d teamsync -Fc > .local/backups/teamsync.dump
docker compose -f compose.dev.yaml exec -T db createdb -U teamsync teamsync_restore
docker compose -f compose.dev.yaml exec -T db pg_restore -U teamsync -d teamsync_restore --no-owner < .local/backups/teamsync.dump
```

복원은 새 DB에 먼저 수행하고 repository/run/finding/user/job 행 수와 migration revision을 확인한다. 실제 운영 전환 전에 복원 DB의 `sessions`를 삭제해 기존 세션을 폐기하고 bootstrap 닫힘·관리자 로그인·미완료 job 재조정을 확인한다. 현재 테스트는 별도 복원 DB의 행 수 일치까지 수행했고 운영 DB로 전환하지 않았다. 덮어쓰기 restore를 자동 수행하지 않는다.

## 문제 해결과 재현

개발 중 DB ID 범위, 동시 PR 생성, 원문 checksum/default 값 차이, legacy null 계약, Docker file secret UID, Cloud 프록시 CA 문제가 있었다. 각각 BigInteger, savepoint 재조회, 원문 hash 보존, nullish 계약, privilege drop, BuildKit CA secret으로 해결했다. CA는 Cloud 검증 빌드에만 주입했으며 TLS 검증을 끄거나 이미지에 인증서 파일을 추가하지 않았다.

단위/PG 검증:

```bash
python -m pip install -e '.[dev,phase2,server]'
ruff check .
pytest -q
# 전용 이름이 _test로 끝나는 PG DB만 허용. DSN은 secret 주입으로 설정한다.
pytest server/tests -q
python -m alembic -c server/alembic.ini upgrade head
python -m alembic -c server/alembic.ini check
npm --prefix web ci
npm --prefix web test
npm --prefix web run build
```

TEST_DATABASE_URL 미설정 시 PG 테스트1개는 명시적으로 skip한다. CI는 PG서비스와 해당 변수를 제공해 skip 없이 실행한다. 독립적 테스트 DB가 필요하며 concurrency 테스트는 자신이 만든 모델 테이블을 삭제한다.

실제 장애 재현 스크립트는 `scripts/validation/`에 있다. **격리된 `teamsync-phase3` 프로젝트 전용**으로 PostgreSQL55432/queue56379/cache56380, validation-admin과 `.local/server/test_admin_password`, 호스트 API8090/실제 worker가 필요하다. 포트 공개는 이 검증에서만 loopback override로 사용했다. 일반 배포나 다른 사람의 DB에 실행하지 않는다. faults/worker_crash/backup_index는 `--owned-validation-project`를 명시해야 한다. backup은 기존 teamsync_restore DB가 있으면 실패하고 덮어쓰지 않는다. index 측정은 전용 teamsync_test DB를 사용한다. live_import는 기존 GH_TOKEN binding을 읽는 호스트 검증이며 기본 Compose에 토큰이 있다고 주장하지 않는다.

`python web/e2e/backend_smoke.py`는 위 격리 설치의13행 기준 브라우저 smoke다. Playwright/Chromium은 검증 도구이며 앱 runtime 의존성이 아니다. 테스트 fixture를 실제 사용자 데이터나 트래픽으로 소개하지 않는다.

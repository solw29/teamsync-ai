# D35 — 실행 제한

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

새 실행 경로는 기본 비활성화하고 제한 컨테이너에서만 실행합니다. import 품질·자원 제한은 D25 이후 확장 전에 선적용했습니다.

현재 상태: **실제 non-root·read-only·network-none 검증**.

관련 파일: `Dockerfile.runner, teamsync/runner_limits.py, container-probe.json`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

생성 코드 실행을 제한한다.

### 완료 기준과 실제 달성

완료 기준: 명시 opt-in·non-root·read-only·network-none·자원 제한과 프로세스 정리를 검증해야 한다.

실제 상태: 실제 UID/쓰기 차단/네트워크 차단/모순 거부 검증. 완전 악성 코드 격리 아님.

### 구현 방법

별도 Docker runner와 Unix resource wrapper를 사용한다.

### 대안과 선택 근거

subprocess timeout만으로는 network/파일 접근을 제한하지 못해 컨테이너 정책을 추가했다. 정적 import 금지는 보조 수단이다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

Docker TLS CA 오류는 임시 BuildKit secret+PIP_CERT로 해결했고 검증을 끄지 않았다. COPY 권한으로 UID65534가 코드를 못 읽던 문제는 명시 소유권/읽기 권한으로 해결했다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

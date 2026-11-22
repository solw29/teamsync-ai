# D23 — 구조화 검사

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

Ruff JSON, pytest JUnit, 선택 Pyright JSON과 실패 원인을 구분합니다.

현재 상태: **구현·실제 도구 검증**.

관련 파일: `teamsync/structured_checks.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

검사 도구의 결과와 장애 원인을 구조화한다.

### 완료 기준과 실제 달성

완료 기준: missing tool/no tests/collection/timeout/diagnostic을 구분하고 측정 대상을 남겨야 한다.

실제 상태: 실제 도구·오류 fixture 검증.

### 구현 방법

Ruff/Pyright JSON, pytest JUnit, 임시 coverage 출력을 사용한다.

### 대안과 선택 근거

로그 문자열 추측보다 도구의 기계 판독 출력과 exit code를 택했다. 해석 실패도 pass로 만들지 않는다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

pytest rootdir에 따라 JUnit classname이 parent prefix를 포함했다. --rootdir=.로 정확한 계약 test ID가 안정되게 했다. 이전 coverage 파일은 사용하지 않고 임시 경로로 새 측정한다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

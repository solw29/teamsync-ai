# D27 — 선택 Notebook 정적 분석

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

옵트인 정적 분석만 지원하며 cell output은 저장하지 않습니다. magic은 unresolved입니다.

현재 상태: **선택 기능 구현·fixture 검증**.

관련 파일: `teamsync/notebooks.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

Notebook을 선택적으로 정적 분석한다.

### 완료 기준과 실제 달성

완료 기준: 출력은 제거하고 code cell/magic/잘못된 JSON/상한을 구분해야 한다.

실제 상태: 정적 fixture 검증, 자동 실행 아님.

### 구현 방법

notebooks.py가 opt-in source AST만 검사한다.

### 대안과 선택 근거

커널 실행보다 정적 분석을 먼저 택해 연구 파일의 구조를 읽되 새 코드 실행 범위를 늘리지 않는다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

잘못된 JSON·cell source 유형이 파서를 중단할 수 있어 environment_error/unresolved로 반환하도록 검증했다. magic은 Python syntax와 같다고 가정하지 않는다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

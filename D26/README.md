# D26 — base/head 영향 분석

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

rename·삭제와 base 호출부를 포함해 보수적 영향 후보를 계산하고 동적 호출은 unresolved로 둡니다.

현재 상태: **구현·rename fixture 검증**.

관련 파일: `teamsync/repository_index.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

삭제·rename의 호출 영향도 추적한다.

### 완료 기준과 실제 달성

완료 기준: head에 사라진 심볼도 base caller를 통해 영향 후보에 남아야 한다.

실제 상태: rename/base caller 회귀 검증.

### 구현 방법

git diff -M과 base/head 간선의 합집합을 역방향 탐색한다.

### 대안과 선택 근거

head만 보는 방식보다 base 간선을 유지해야 삭제된 함수의 기존 호출부를 잃지 않는다. 정적 근사이며 런타임 추적보다 비용이 작다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

rename fixture로 caller.main이 유지되는 것을 검증했다. 동적 메서드는 잘못 확정하지 않고 unresolved다. 실제 운영 장애 사례로 꾸미지 않는다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

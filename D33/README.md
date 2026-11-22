# D33 — 호출 한도와 사용량

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

JSON 입력 문자·출력 token·run별 호출 1회 한도를 둡니다. 실제 usage가 없으면 null, 비용 단가가 없으면 null입니다.

현재 상태: **구현·상한 및 null 검증**.

관련 파일: `teamsync/analyze.py, teamsync/phase2_config.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

실행별 호출 제한과 사용량을 보존한다.

### 완료 기준과 실제 달성

완료 기준: 입력 상한 초과 시 호출0, 응답 usage가 없으면 null, 한 실행 호출1을 지켜야 한다.

실제 상태: 상한/미측정 검증 및 새 호출6회 token 기록.

### 구현 방법

전체 JSON 입력 문자 수·max output tokens·실측 usage와 config hash를 사용한다.

### 대안과 선택 근거

임의 비용 추정이나 누락0보다 null을 택했다. 중앙 승인 없이 전역 일일 한도를 보장할 수 없기 때문이다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

diff만 자르면 checks/contracts가 상한을 넘을 수 있었다. 직렬화한 전체 사용자 JSON을 검사해 초과 요청을 차단했다. system/schema token까지의 정확한 사전 상한은 주장하지 않는다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

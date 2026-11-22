# D31 — 보수적 요구사항 판정

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

정확히 매핑된 테스트 실행 근거가 있어야 satisfied/violated이며 심볼 존재만으로 충족을 확정하지 않습니다.

현재 상태: **구현·세 판정 회귀 검증**.

관련 파일: `teamsync/requirements.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

요구사항을 보수적으로 판정한다.

### 완료 기준과 실제 달성

완료 기준: 명시 심볼·호출 경로·실제로 실행한 테스트가 있어야 satisfied/violated, 부족하면 unverifiable다.

실제 상태: 세 판정·unconnected·truncation 회귀 통과.

### 구현 방법

judge가 static reachability와 JUnit pass/fail을 함께 요구한다.

### 대안과 선택 근거

AST 존재나 전체 pytest green만으로 판정하면 unrelated test가 근거가 된다. 정확한 계약과 호출 연결을 결합했다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

대상을 호출하지 않는 green test의 잘못된 만족 가능성을 회귀 테스트로 재현해 차단했다. 런타임 모든 분기의 호출 증명은 아니다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

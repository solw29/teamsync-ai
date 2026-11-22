# D22 — v2 계약과 manifest

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

실행 identity·요구사항 판정·근거·사용량을 분리하고 v1 호환을 유지합니다.

현재 상태: **구현·로컬 검증**.

관련 파일: `teamsync/phase2_schema.py, docs/phase2/report-v2.schema.json`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

v2 run 보고서와 manifest 계약을 만든다.

### 완료 기준과 실제 달성

완료 기준: identity·버전·근거 참조·checksum을 검증하고 v1을 계속 받아야 한다.

실제 상태: 왕복·변조·identity 실패 검증. 출처 권한은 API 수집에서 따로 확인.

### 구현 방법

phase2_schema.py의 RunReport/Manifest와 detached SHA256, schema별 UI adapter를 만들었다.

### 대안과 선택 근거

v1을 직접 갈아엎기보다 별도 v2를 택해 보존된12개 결과와 신규 실행을 함께 읽게 했다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

ISO timestamp의 +00:00과 프런트엔드 Z 검증 차이가 있어 Z 형식으로 정규화했다. checksum은 인증으로 취급하지 않는다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

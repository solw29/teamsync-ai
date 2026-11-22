# D25 — 제한 AST 인덱스

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

추가 줄 diff와 별개로 Git 객체를 크기·파일 수 한도 내에서 정적 분석합니다.

현재 상태: **구현·로컬 검증**.

관련 파일: `teamsync/repository_index.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

diff와 별개인 정적 인덱스를 만든다.

### 완료 기준과 실제 달성

완료 기준: base/head Python을 한도 내 파싱하고 syntax/limit/dynamic을 명시해야 한다.

실제 상태: 제한 인덱스 검증. 동적 분석 완전성 보장 아님.

### 구현 방법

Git blob을 읽는 repository_index.py와 ast visitor를 사용한다.

### 대안과 선택 근거

target import보다 AST를 택해 정적 분석 단계에서 코드를 실행하지 않는다. 전체파일 무제한보다 파일/byte 한도를 둔다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

루프 변수를 visitor 메서드가 늦게 참조한다는 lint 지적이 나왔다. 생성 시 mod/path/aliases를 객체에 바인딩해 파일 간 혼동을 막았다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

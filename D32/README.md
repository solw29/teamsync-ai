# D32 — 선택 LLM 라우팅

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

off/always/selective와 선택 사유를 기록합니다. skipped를 의미적 정확성으로 바꾸지 않습니다.

현재 상태: **구현·offline 라우팅 검증**.

관련 파일: `teamsync/llm_router.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

의미 검토가 필요한 입력만 선택한다.

### 완료 기준과 실제 달성

완료 기준: off/always/selective와 선택 사유·미검토 범위를 남겨야 한다.

실제 상태: offline 결정 검증. 전역 비용 hard cap 아님.

### 구현 방법

llm_router.py가 명시 실패/충족과 근거 부족을 분리한다.

### 대안과 선택 근거

항상 LLM을 호출하기보다 확정 검사 결과의 중복 설명을 줄이고 unknown을 검토 대상으로 남겼다. 실제 token 절감률은 별도 측정이 필요하다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

green checks를 의미 정확성으로 오해할 수 있어 skipped에 not_assessed를 보존한다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

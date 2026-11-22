# D37 — Workflow와 필수 상태

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

실패·중단 후에도 보고서 job이 실행되며 필수 gate가 JSON 기록과 별개로 실패를 반환합니다. 프로덕션 경로는 병합 후 base 도구로 활성화됩니다.

현재 상태: **구현·실제 draft PR CI 및 run report 검증 완료**.

관련 파일: `.github/workflows/teamsync.yml, .github/workflows/phase2-validation.yml`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

보고서와 필수 CI 결론을 분리한다.

### 완료 기준과 실제 달성

완료 기준: 필수 실패는 nonzero, LLM skip은 중립이며 실패 때도 보고서 생성 경로가 있어야 한다.

실제 상태: gate/부분 보고서 검증. main 활성화는 병합 후다.

### 구현 방법

always report job과 required-verification gate를 분리했다.

### 대안과 선택 근거

JSON에 failed를 썼다고 job이 실패하지는 않아 별도 gate를 선택했다. optional AI와 필수 검사 실패를 하나의 결론으로 숨기지 않는다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

초기 collect의 정상 종료가 pytest 실패를 workflow 성공처럼 보이게 했다. 필수 집계 검사를 추가하고 루트 정책 파일의 초기 staging 누락도 별도 commit으로 보완했다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

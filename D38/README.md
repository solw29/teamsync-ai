# D38 — React v2 근거 화면

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

기존 12개 v1 Import와 v2 adapter, Evidence 탭·미측정 usage·모바일을 검증합니다.

현재 상태: **빌드·9개 단위·브라우저 검증**.

관련 파일: `web/src/schema.ts, web/src/main.tsx, web/e2e/phase2_smoke.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

v2 근거 화면과 v1 호환을 검증한다.

### 완료 기준과 실제 달성

완료 기준: 실제 v2 import·근거/판정/미측정 usage와 기존12개 v1을 모두 표시해야 한다.

실제 상태: 9개 frontend·브라우저·build 통과.

### 구현 방법

Zod version adapter와 Evidence 탭을 추가했다.

### 대안과 선택 근거

v1 DTO를 서버 계약으로 바꾸기보다 변환 계층으로 UI를 유지해 이전 파일을 계속 읽게 했다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

Evidence 추가 후 모바일 탭이 가로로 넘쳤다. 탭 wrap과 본문 overflow-wrap을 적용하고 390px에서 실제 overflow가 없음을 확인했다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

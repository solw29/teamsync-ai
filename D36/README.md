# D36 — 실행별 보고서 통합

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

repo ID·SHA·workflow·run·attempt와 도구/설정 버전을 고정하고 report+manifest를 생성합니다. fixture 예제는 실제 GitHub run으로 가장하지 않습니다.

현재 상태: **구현·checksum/identity/부분 실패 검증**.

관련 파일: `teamsync/phase2_cli.py, docs/phase2/example-v2/`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

실제 run/attempt 보고서를 만든다.

### 완료 기준과 실제 달성

완료 기준: repo ID·SHA·workflow/run/attempt·버전·checksum이 실제 API와 일치해야 한다.

실제 상태: 실제 run2건 보존·API 대조. checksum만으로 권한 인증하지 않는다.

### 구현 방법

phase2_cli report와 detached manifest를 생성해 실제 PR CI artifact를 다운로드 검증했다.

### 대안과 선택 근거

기존 D6 전용 Exporter보다 실행별 불변 보고서가 후속 pull 수집과 중복 방지의 기준이 된다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

workflow ref를 numeric workflow ID로 오인할 여지가 있어 실제 GitHub run metadata로 ID를 조회했다. 정책과 계약을 함께 fingerprint한다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

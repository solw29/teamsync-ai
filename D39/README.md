# D39 — 새 평가와 이력 분리

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

깨끗한 수기 계약 6쌍과 3개 holdout의 검증 불가 처리를 확인합니다. 새 모델 평가와 과거 D6 수치는 서로 다른 결과로 기록합니다.

현재 상태: **offline 검증 완료·실제 모델 결과는 validation 참조**.

관련 파일: `teamsync/phase2_evaluate.py, offline-contract-evaluation.json, tests/fixtures/phase2/holdout.json`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

# D37 — Workflow와 필수 상태

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

실패·중단 후에도 보고서 job이 실행되며 필수 gate가 JSON 기록과 별개로 실패를 반환합니다. 프로덕션 경로는 병합 후 base 도구로 활성화됩니다.

현재 상태: **구현·실제 draft PR CI 검증 대기**.

관련 파일: `.github/workflows/teamsync.yml, .github/workflows/phase2-validation.yml`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

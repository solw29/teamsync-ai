# D33 — 호출 한도와 사용량

실제 작업일: 2026-11-22 (KST). 날짜 없는 D번호 폴더로 기록합니다.

## 작업과 상태

JSON 입력 문자·출력 token·run별 호출 1회 한도를 둡니다. 실제 usage가 없으면 null, 비용 단가가 없으면 null입니다.

현재 상태: **구현·상한 및 null 검증**.

관련 파일: `teamsync/analyze.py, teamsync/phase2_config.py`.

## 재현·증거

공통 명령: `python -m pytest -q`, `ruff check .`, `npm --prefix web test`, `npm --prefix web run build`. 관련 테스트는 `tests/phase2/`, 브라우저 검증은 `web/e2e/phase2_smoke.py`입니다.

[설계·범위](../docs/phase2/README.md)와 [실행 명령·결과·미검증](../docs/phase2/validation.md)을 확인하세요. 계획상의 완료 기준과 실제 결과를 혼동하지 않습니다. 다음 차수는 자동 진행하지 않습니다.

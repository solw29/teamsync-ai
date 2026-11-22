# 2차 검증 기록 — 2026-11-22 (KST)

| 검증 항목 | 실제 결과 | 범위/한계 |
|---|---|---|
| 기준선 | Python 27/27, frontend 6/6 | 880f277, D1~D20 및 D6 raw evidence 보존 |
| 확장 회귀 | 최종 수치는 아래 CI 기록으로 확정 | pytest testpaths로 artifacts의 우연한 테스트 수집 배제 |
| Web | 9/9 및 build 통과 | v1 12개, v2, identity 불일치·dangling evidence·알 수 없는 버전 |
| 브라우저 | v1/v2 import, Evidence, null usage, mobile, v1 복귀 통과 | desktop 1440×960, mobile 390×844, pageerror 없음 |
| 구조화 검사 | no-tests·collection error·실패·timeout·tool missing 구분 | 실제 pytest와 임시 fixture |
| Pyright | 반환 타입 오류 감지 | Pyright 1.1.414의 실제 JSON diagnostic |
| Coverage | 대상 sample, 기준90%, 측정100% | 작은 fixture에서만 검증, 품질 지표로 주장하지 않음 |
| 정적 영향 | rename 후 base caller 영향 유지 | dynamic은 unresolved, 전역 그래프 정확도 주장 안 함 |
| 요구사항 | 명시 테스트 pass/fail/부족을 구분 | 심볼 단독 만족 불가, 잘린 인덱스 unverifiable |
| 제한 컨테이너 | UID65534·대상 쓰기 차단·네트워크 차단 | D35/container-probe.json, 악성 코드 완전 격리 주장 안 함 |
| 생성 코드 | 독립 import가 있는 통제된 초안 통과 | D35/controlled-test-result.json, 모델 품질 실적과 구분 |
| v2 manifest | checksum 변경·identity 불일치·잘못된 SHA·부분 결과 검증 | checksum은 인증 아님 |
| Notebook | 정적 opt-in·magic unresolved·output 미보존 | 자동 실행은 선택 기능으로 미구현/미실행 |
| offline 계약 쌍 | 버그6개 violated / 수정6개 satisfied | 새 수기 계약 실행이며 LLM 성능 아님 |
| Holdout 3개 | 근거 부족 시 unverifiable | 모델에 전송 안 함, 품질 개선에 재사용 안 함 |

## 재현 명령

```bash
python -m pip install -e '.[dev,phase2]'
ruff check .
pytest -q
npm --prefix web ci
npm --prefix web test
npm --prefix web run build
# Vite 실행 후
python web/e2e/phase2_smoke.py
python -m teamsync.phase2_evaluate
```

Docker의 기본 build는 Cloud proxy CA가 내장되지 않아 실패했고, `docs/phase2/README.md`에 기록한 임시 BuildKit CA mount로 TLS 검증을 유지하며 성공했습니다. 일반 GitHub runner의 표준 Dockerfile 검증은 PR CI로 별도 확인합니다.

## 실제 GitHub 실행 증거

검토용 draft PR을 만든 뒤 Phase 2 verification workflow에서 current PR SHA·repo ID·run ID·attempt의 report와 manifest를 생성·다운로드해 검증할 예정입니다. 이 문단은 실제 run URL과 다운로드 검증 결과로 갱신합니다. main의 프로덕션 리뷰 workflow는 아직 병합되지 않아 활성화됐다고 표시하지 않습니다.

## 새 LLM 품질 평가

선택 LLM이 확정 계약 오류의 중복 설명을 생략하는 결정은 offline으로 확인했습니다. 별도 수동 workflow는 한 실행에 하나의 알려진 합성 사례·LLM 1회만 호출하고, 같은 초안을 버그/수정 양쪽 제한 컨테이너에서 실행합니다. 결과가 나오기 전까지 모델 검출·token 절감·개선률을 제시하지 않습니다. 과거 D6의 3/6쌍·6/30·오탐2는 이번 실적으로 세지 않습니다.

## 남은 검수와 다음 차수

D28 Notebook 자동 실행은 선택 항목으로 제외했습니다. 독립된 사람의 요구사항/오탐 판정과 유지보수자의 PR 검토는 대체하지 않습니다. 새로운 3차 API/DB/큐는 이번 작업에 포함하지 않습니다. 모든 필수 근거와 실제 run report 검증 뒤에도 main 병합은 사용자가 결정합니다.

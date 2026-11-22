# 2차 D21~D40 구현 기록

기준 문서: `TeamSync_AI_방향검토_3-5차_상세계획.docx` (사용자 제공, 2026-11-22 검토본).
요청 범위는 2차까지입니다. 3차 API·DB·큐·캐시, 4차 설치판, 5차 키 등록 UI는 추가하지 않습니다.

원본 D1-D50 상세 계획서는 이번에 첨부되지 않았습니다. 따라서 현재 DOCX의 명시 항목으로 아래 번호를 매핑했습니다. 문서의 공통 지시 중 ‘작업 하나만’은 사용자가 요청한 D21~D40 일괄 진행 범위와 달라, 각 단계를 나눠 구현·검증하되 같은 검토 브랜치에 묶었습니다. main 자동 병합과 환경 Publish는 하지 않습니다.

## 실행·결과 계약

- `teamsync-policy.json`: trusted base/tool checkout에서만 읽습니다. 임의 shell 명령 설정은 없습니다. 검사명 허용 목록·자원 상한·선택 LLM·생성 테스트 opt-in을 명시합니다.
- `teamsync-requirements.json`: trusted base의 명시 계약. `description`은 의도, `symbol`은 후보 연결, `testIds`는 JUnit의 정확한 `classname::name`입니다. 값이 없으면 충족 판정하지 않습니다. 예제는 contracts.example.json입니다.
- `phase2_cli collect`: target를 검사하는 단계이며 독립 runner에서만 실행합니다. Git base/head 객체를 별도로 AST 인덱싱하고 diff·구조화 검사·명시 계약 판정을 저장합니다.
- `phase2_cli analyze`: JSON만 읽고 고정 LLM endpoint를 선택적으로 호출합니다. JSON 입력 문자 상한·출력 token 상한·호출 1회 상한을 적용합니다. 이는 전역 일일 비용 hard cap이 아닙니다. 입력 token의 정확한 사전 상한을 보장하지 않습니다.
- `phase2_cli execute`: 기본 비활성화. 신뢰 팀원 범위에서 명시 opt-in한 경우에만 제한 컨테이너에서 초안을 실행합니다. 정적 draft 거부 규칙은 격리 수단이 아닙니다.
- `phase2_cli report`: 실제 event의 repo ID·PR·SHA, run ID·attempt·workflow와 도구/설정 버전을 보존하고 report.json 및 detached manifest.json SHA256을 생성합니다. checksum은 출처 인증이 아닙니다.
- `phase2_cli gate`: JSON 기록 여부와 무관하게 필수 검사 누락/실패 및 명시 계약 위반 시 nonzero로 종료합니다. LLM skipped는 필수 검사 실패로 바꾸지 않습니다.

CLI 기본 출력은 `artifacts/`, `report-output/`이며 예시는 아래와 같습니다. 실제 PR 이벤트와 메타데이터를 사용해야 합니다.

```bash
python -m pip install -e '.[dev,phase2]'
BASE_SHA=<40자리> HEAD_SHA=<40자리> python -m teamsync.phase2_cli collect --target target
python -m teamsync.phase2_cli analyze
GITHUB_EVENT_PATH=<PR-event.json> GITHUB_RUN_ID=<id> GITHUB_RUN_ATTEMPT=<attempt> python -m teamsync.phase2_cli report
python -m teamsync.phase2_cli gate
python -m teamsync.phase2_evaluate
```

## v1/v2 UI

기존 12개 v1 데이터 import를 보존하고 v2는 독립 adapter로 변환합니다. v2 상세의 Evidence 탭에서 계약/심볼/실행 테스트, 충족/위반/검증불가, 실행 오류 원인, 사용량 미측정을 나눠 표시합니다. 웹 import는 JSON 구조·identity 일치·evidence 참조를 검증합니다. manifest checksum 검증은 Python `load_report`가 수행합니다. 브라우저가 체크섬만으로 GitHub 출처를 인증하지 않습니다.

`example-v2/`는 실제 로컬 fixture 테스트를 실행해 만든 **가상 GitHub identity의 예제**입니다. 새 GitHub 실측이나 새로운 모델 성능을 뜻하지 않습니다. 실제 CI run report와 URL은 validation.md에 별도로 기록합니다.

## 판단 범위와 한계

정적 호출 그래프는 직접 이름·명시 import의 제한된 연결만 확인합니다. 동적 호출·외부 라이브러리 호출·모호한 메서드·인덱스 제한은 unresolved/warnings로 남깁니다. 대형 레포 전체 의존성 정확도를 보장하지 않습니다. 삭제·rename 영향은 base와 head의 호출 간선을 함께 사용합니다.

요구사항 `satisfied`는 명시 심볼과 연결된 모든 이름의 테스트가 실제 통과한 범위만 의미합니다. 그 테스트의 기대값이나 요구사항 전체 품질을 독립적으로 입증하지 않습니다. 테스트 없음·미매핑·잘린 인덱스는 unverifiable입니다. AST 존재만으로 만족을 만들지 않습니다.

Pyright와 coverage는 opt-in입니다. 커버리지 대상과 최소값을 함께 저장하고 측정이 없으면 environment_error로 남깁니다. 높은 커버리지를 테스트 품질로 소개하지 않습니다. 생성 테스트의 requirementIds는 대상 함수 연결이며 기대값의 독립 검증 상태는 별도로 미검증입니다.

Notebook 정적 분석은 opt-in, 셀 출력은 보존하지 않고 magic은 unresolved로 둡니다. Notebook 자동 실행(D28)은 선택 기능으로 이번에 구현·실행하지 않았습니다. 새 자동 실행 범위를 늘리지 않았습니다.

## 실행 제한과 검증 재현

`Dockerfile.runner`는 target를 install/import하는 secret job에서 빌드하지 않습니다. 생성 코드 실행 job은 LLM/Discord 키와 쓰기 토큰을 받지 않습니다. network none, read-only root/target, tmpfs, cap-drop ALL, no-new-privileges, uid65534, memory/CPU/PID 및 subprocess resource ceiling을 사용합니다. timeout 시 process group을 정리합니다. 완전 악성 코드 격리는 주장하지 않습니다.

로컬 Cloud에서는 기본 Docker 빌드에 proxy CA가 없어 TLS 오류가 발생했습니다. 검증을 끄지 않고, 임시 Dockerfile에 BuildKit secret CA mount와 PIP_CERT를 지정해 해결했습니다. CA는 소스나 이미지 레이어에 복사하지 않았습니다. 일반 GitHub runner용 Dockerfile은 표준 TLS 검증을 그대로 사용합니다. non-root COPY 권한 문제도 읽기 전용 권한/소유자로 해결하고 다시 실행했습니다.

## 평가 원칙

D6 과거 12 PR·6쌍·30초안의 원본은 그대로 보존합니다. D39의 새 결과는 수기 계약 테스트와 deterministic router의 offline 비교입니다. 모델 호출을 수행하지 않았으므로 새 LLM 정확도·실측 비용 감소라고 주장하지 않습니다. 독립 holdout 3개는 요구사항 정보가 부족하면 unverifiable로 유지되는 회귀 검증에만 쓰며 모델에 전송하지 않았습니다. 새 모델 전후 평가·독립 사람 판정은 미완료로 남깁니다.

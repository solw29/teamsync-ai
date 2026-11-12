# TeamSync AI

Python PR의 추가된 diff와 ruff·pytest 결과로 AI 리뷰와 테스트 초안을 만들고, 위치를 검증한 리뷰만 PR 댓글에 게시합니다. Discord Webhook으로 완료 상태를 알립니다. 테스트는 자동 커밋하지 않습니다.

## 현재 상태와 기준

일정은 **상세계획 C의 1인·10일 계획**, 구조·보안은 **상세계획 G**를 따릅니다. 날짜 폴더는 계획상의 11월 2일~11일을 의미하며 실제 작업 완료 날짜를 소급 주장하지 않습니다.

기존 D2에는 루트의 CI 초안·검사 모델만 있었으며 패키지와 실제 workflow 경로가 빠져 있었습니다. 이를 보완했습니다. D3~D5 파이프라인과 D6 오프라인 평가 도구를 구현했습니다. 실서비스 연결·실제 PR 평가·영상·최종 리허설은 아래 문서의 미완료 항목으로 남아 있습니다.

## 로컬 개발

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
pytest -q
python -m teamsync.evaluate
```

`teamsync.evaluate`는 직접 작성한 계약 테스트를 6개 버그/수정 코드 쌍에 실행합니다. LLM 평가나 PR 실측을 대신하지 않습니다. 생성 테스트 실행기는 개발 머신에서 실행하지 마세요. `TEAMSYNC_DISPOSABLE_RUNNER`는 격리 수단이 아니라 오용 방지 가드이며, 생성 코드는 임의 Python입니다.

## GitHub Actions 설정

1. 이 변경을 `main`에 반영합니다. 분석 도구는 PR의 **base SHA**에서 읽으므로 이 코드가 base에 있어야 합니다.
2. 저장소 Actions Secrets에 `LLM_API_KEY`(OpenAI API), `DISCORD_WEBHOOK_URL`을 설정합니다. 선택 변수 `LLM_MODEL`의 기본값은 `gpt-4o-mini`입니다. 비밀값을 파일·댓글에 쓰지 않습니다.
3. 같은 저장소 브랜치에서 소형 Python PR을 엽니다. `.github/workflows/ci.yml`이 프로젝트를 검사하고 `teamsync.yml`이 검사 → 선행 댓글 → 분석 → 격리 실행 → 최종 댓글·알림을 수행합니다.
4. 봇 댓글 하나가 갱신되는지, Discord 알림이 도착하는지 확인합니다. 키가 없으면 AI는 `missing_input`, API/스키마 오류는 `error`, 실행되지 않은 테스트는 미실행으로 표시합니다. 검사 결과는 AI 대기 전에 먼저 게시합니다. 최종 분석 잡 실패 시에도 검사 결과를 재게시합니다.

분석 잡만 LLM 키를, 최종 게시 잡만 Discord Webhook과 PR 쓰기 토큰을 사용합니다. PR 코드를 실행하는 검사·생성 테스트 잡에는 이 시크릿을 전달하지 않고 checkout 인증도 저장하지 않습니다. 생성 테스트에는 30초, 잡에는 5분 제한이 있습니다. 호스팅 runner는 잡마다 폐기됩니다. 네트워크 차단·강한 OS 샌드박스는 제공하지 않으므로 **비공개 데모 저장소와 신뢰하는 팀원만 지원**합니다. 악성 PR·fork PR은 지원하지 않습니다. workflow 변경은 시크릿 실행 전 검토하며, 브랜치 보호/리뷰 정책은 저장소 관리자가 설정해야 합니다. `pull_request_target`은 사용하지 않습니다.

PR의 추가 코드와 검사 로그 일부가 외부 LLM API로 전달됩니다. 비밀·개인정보가 포함된 저장소에 적용하지 마세요. 입력은 300개 추가 줄·약 24,000자로 제한하며 제외·생략 여부를 댓글에 표시합니다. 파일·줄 존재 검증은 리뷰 내용의 진실성 검증이 아닙니다.

## 일정별 기록

- [D1 설계](1102_D1/d1-design.md), [평가 계약](1102_D1/seed-pr-matrix.csv)
- [D2 기존 기록](1103_D2/README.md)
- [D3 diff·분석](1104_D3/README.md)
- [D4 검증·부분 게시·Discord](1105_D4/README.md)
- [D5 생성 테스트](1106_D5/README.md)
- [D6 평가](1107_D6/README.md)
- [D7 보안·선택 기능 결정](1108_D7/README.md)
- [D8 안정화](1109_D8/README.md)
- [D9 발표·백업](1110_D9/README.md)
- [D10 리허설](1111_D10/README.md)

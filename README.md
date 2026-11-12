# TeamSync AI

Python PR의 추가된 diff와 ruff·pytest 결과로 AI 리뷰와 테스트 초안을 만들고, 위치를 검증한 리뷰만 PR 댓글에 게시합니다. Discord Webhook으로 완료 상태를 알립니다. 테스트는 자동 커밋하지 않습니다.

## 현재 상태와 기준

일정은 **상세계획 C의 1인·10일 계획**, 구조·보안은 **상세계획 G**를 따릅니다. 날짜 폴더는 계획상의 11월 2일~11일을 의미하며 실제 작업 완료 날짜를 소급 주장하지 않습니다.

기존 D2에는 루트의 CI 초안·검사 모델만 있었으며 패키지와 실제 workflow 경로가 빠져 있었습니다. 이를 보완했습니다. D3~D5 파이프라인과 D6 오프라인 평가 도구를 구현했습니다. 2026-11-12 실제 PR 12개와 동일 초안 6쌍 평가를 완료하고 실제 PR 화면 백업 영상을 녹화했습니다. [실측 보고서](1107_D6/live-report.md)와 [영상](1110_D9/recording.md)을 확인하세요. 생성 테스트 검출은 3/6쌍이며 오탐 2건이 있어 품질 개선이 필요합니다. Discord HTTP 성공과 사용자 확인을 통한 채널 수신까지 검증했습니다. 사람 발표 리허설은 남아 있습니다.

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

## React Review Dashboard (D11~D20 확장)

별도 `web/` React·TypeScript·Vite SPA에서 D10 결과를 탐색합니다. 기존 PR 파이프라인과 별개이며 브라우저에는 시크릿이 없습니다.

```bash
python -m teamsync.export_report --evidence 1107_D6/live-evidence --output artifacts/report.json
cd web
npm ci
npm run dev
```

Data import에서 결과 파일을 선택하면 Dashboard·상세·Evaluation 전체에 반영됩니다. 공개 기본 데모는 익명화되어 코드 링크와 원본 테스트를 제공하지 않습니다. 실제 결과를 가져오면 SHA 고정 코드 링크와 테스트 초안을 확인할 수 있습니다.

[설계](docs/react-extension-design.md) · [결과 계약](docs/result-schema.md) · [웹 실행·배포 안내](web/README.md) · [통합 검증 기록](docs/react-test-report.md)

`.github/workflows/dashboard.yml`은 별도 빌드·테스트 후 import JSON과 정적 빌드를 artifact로 저장합니다. 기존 PR workflow를 변경하지 않습니다. 정적 호스팅 설정은 준비했으나 외부 배포는 아직 수행하지 않았습니다.

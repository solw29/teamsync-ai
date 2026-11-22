# TeamSync AI

GitHub PR의 변경 코드와 린트·테스트 결과를 분석해 AI 리뷰와 테스트 코드 초안을 제공하고,
결과를 Discord로 알리는 팀 개발 보조 도구입니다.

## MVP 범위

- Python 저장소와 같은 저장소 브랜치의 PR
- GitHub Actions에서 `ruff`, `pytest`, diff 수집 실행
- LLM이 구조화된 리뷰와 테스트 코드 초안 생성
- 파일·줄 위치를 diff와 대조한 뒤 PR 댓글 갱신
- Discord Webhook으로 결과 알림
- 생성 테스트는 자동 커밋하지 않고 실행 상태만 표시

일정 조율, Slack, 공개 GitHub Action 패키징은 핵심 MVP 이후 범위입니다.

## 현재 상태

D1: 범위·보안 정책·시드 PR 평가 사례 설계 완료.
D2: Python 패키지 기본 구조와 검사 결과 모델을 준비하고, PR에서 `ruff`와 `pytest`를 실행하는 GitHub Actions workflow를 구성했습니다.

## 개발 환경

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
ruff check .
pytest -q
```

## GitHub Actions

`.github/workflows/ci.yml`은 `main`을 대상으로 열린 PR의 생성·갱신·재오픈·초안 해제 시 실행됩니다. 초안 PR은 검사하지 않으며, 같은 PR의 새 실행이 시작되면 이전 실행을 취소합니다. 이 단계에서는 코드 읽기 권한만 사용하고 저장소 Secret은 필요하지 않습니다.

## 문서

- [D1 설계 및 보안 정책](../1102_D1/d1-design.md)
- [시드 PR 평가 사례](../1102_D1/seed-pr-matrix.csv)

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

Python 패키지와 CI 검사 기반을 만든다.

### 완료 기준과 실제 달성

완료 기준: 설치 후 ruff·pytest가 실행되고 올바른 workflow 경로에서 PR 검사가 시작돼야 한다.

실제 상태: 보완 후 설치·CI 검증됨. 초기 D2 기록의 완료 서술은 보완 이전 상태와 구분한다.

### 구현 방법

pyproject.toml과 teamsync 패키지를 추가하고 루트 ci.yml을 .github/workflows/ci.yml로 옮겼다.

### 대안과 선택 근거

각 컴퓨터의 임의 검사보다 CI에 고정 명령을 두어 재현성을 확보했다. 패키지 설치 없이 sys.path를 수동 조정하는 방법은 유지보수 경로가 늘어 제외했다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

초기 D2 업로드에는 패키지 manifest가 없고 workflow가 루트에 있어 실행되지 않았다. 실제 설치 실패를 확인한 뒤 패키지 구조와 workflow 위치를 보완했다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

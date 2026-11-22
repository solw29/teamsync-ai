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

## 개발 환경

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
```

## 문서

- [D1 설계 및 보안 정책](../1102_D1/d1-design.md)
- [시드 PR 평가 사례](../1102_D1/seed-pr-matrix.csv)

## 구현 판단과 완료 기준 검토 (2026-11-23)

### 작업

범위·시드 계약·시크릿 정책을 정리한다.

### 완료 기준과 실제 달성

완료 기준: Python·동일 저장소 PR 범위, 6개 시드 계약과 키 분리 정책을 문서로 확인할 수 있어야 한다.

실제 상태: 설계 산출물 완료. 실제 키 연결·운영 보안 전체 검증을 뜻하지 않는다.

### 구현 방법

1102_D1/d1-design.md와 seed-pr-matrix.csv에 계약을 고정했다.

### 대안과 선택 근거

서버 중심 분석이나 여러 언어 동시 지원보다 Actions+Python을 택했다. 1인 MVP에서 기존 runner와 PR 이벤트를 재사용할 수 있기 때문이다. FastAPI/Slack 확장은 당시 제외했다. 이는 현재 코드와 기록을 대조한 설계 판단이며, 수행하지 않은 대안 간 성능 비교 실험을 뜻하지 않습니다.

### 개발 중 문제·해결·남은 한계

README의 docs/ 상대 링크가 실제 위치와 달랐다. 현재 문서 위치 기준 링크로 고쳤다. 당시 pip 설치 명령은 패키지 설정이 없어 실행 불가했으며 D2 보완에서 해결했다.

증거는 이 README의 관련 파일·검증 기록과 연결합니다. 운영 장애 기록이 없는 설계 위험은 실제 운영 장애로 주장하지 않습니다. 숫자는 각 차수의 실행 기록을 따르며, 이전 통과 수를 현재 코드의 새 실적으로 재사용하지 않습니다.

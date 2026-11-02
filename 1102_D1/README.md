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

- [D1 설계 및 보안 정책](docs/d1-design.md)
- [시드 PR 평가 사례](docs/seed-pr-matrix.csv)

# D50 — 백엔드 통합 검수와 성능 기준선

DOCX 3-10 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

Actions artifact→queue→PG→API→React 통합, 장애 복구·cache/index 측정을 기록하고 CI를 추가한다.

## 완료 기준과 실제 확인

핵심 테스트와 실제 장애 시험을 통과하고 실제/합성 표본을 구분한다. 새 PR artifact 수집과 CI 결과는 검수 문서에 추적한다.

[통합 검수](../docs/backend-validation.md), [합성 index](../docs/backend/evidence/index-measurement.json), [운영 가이드](../docs/backend/README.md).

## 어떤 기능을 어떻게 구현했는가

실제 12개 보존 결과+v2와 production queue 경로를 사용한다. cache 전후는 같은13행/100회, index 전후는 격리된 test DB의10만 합성행/30회로 측정한다. 운영 DB 인덱스를 제거하지 않는다. backend CI는 실제 PG 동시성·migration drift·React build·Docker build를 검사한다.

## 다른 방법과 선택 근거

단위 테스트만으로 컨테이너/네트워크/영속 복구를 보장할 수 없다. 반대로 모든 부하를 실제 사용자 성능처럼 표시하지 않고 동일 환경·분모·샘플을 명시한다. PR은 이전 단계 브랜치 위에 쌓아 review 가능한 상태로 둔다.

## 개발 중 문제와 해결·남은 한계

작은 데이터 cache p95 개선이 없고 Starlette TestClient의 httpx deprecation 경고가 남아 있다. 경고를 숨기지 않고 현재 통과 상태와 함께 기록한다. 4·5차 설치 wizard/역할 고도화는 이번 구현으로 표시하지 않는다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

# D47 — 통계 캐시와 일관성

DOCX 3-07 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

저장소 통계에만 Cache Aside를 적용하고 cache와 queue Redis를 분리한다.

## 완료 기준과 실제 확인

권한 확인 후 통계 조회, commit 버전 변경 후 이전 키 미사용, cache 장애 시 DB fallback과 실제 시간/쿼리 수를 기록한다.

[측정·cache 중단](../docs/backend/evidence/faults-performance.json). TTL은 외부에서 DB를 직접 수정하는 상황까지 즉시 반영하지 않으며 운영 변경은 저장 API를 사용해야 한다. 단위 테스트의 메모리 cache는 TTL 시간을 모사하지 않는다.

## 어떤 기능을 어떻게 구현했는가

`cache.py`에서 deployment/owner/repository/days/version 키와 TTL30초를 사용한다. 매 요청 DB의 현재 stats_version을 읽으므로 commit 뒤 old cache가 남아도 사용하지 않는다. 목록·상세는 캐시하지 않는다.

## 다른 방법과 선택 근거

전체 응답 캐시는 필터/권한/무효화 조합이 복잡하다. 통계 한 종류부터 적용하면 측정과 장애 격리가 쉽다. Redis Pub/Sub 무효화보다 DB 버전 키가 삭제 실패 시에도 일관성 경계를 유지한다.

## 개발 중 문제와 해결·남은 한계

캐시가 있다고 항상 빨라지지 않았다. 실제 13행×100회에서 SQL은 200→100회, p50은 1.566→1.233ms였지만 p95는 2.086→2.834ms였다. 네트워크 왕복 때문에 작은 표본의 tail 개선을 주장하지 않는다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

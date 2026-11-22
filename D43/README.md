# D43 — 조회 API와 페이지네이션

DOCX 3-03 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

인증된 runs 목록/상세, PR 이력, 저장소 통계와 OpenAPI·React 계약 fixture를 추가한다.

## 완료 기준과 실제 확인

다른 소유자 접근 차단, 없는 ID·오류 cursor·필터·동시 삽입과 페이지 경계를 시험한다. Python 응답과 React Zod 계약을 실제 fixture로 검사한다.

`test_cursor_stability...` 계열과 API 권한 테스트, frontend FastAPI fixture 파싱 테스트; [계약](../docs/backend/contract/openapi.json).

## 어떤 기능을 어떻게 구현했는가

`main.py`, `schemas.py`와 `docs/backend/contract/`에서 `(created_at,id)` cursor를 사용한다. 리뷰 수 정렬은 finding_count도 포함한다. cursor에 필터 바인딩을 넣고 잘못된 조합을 거부한다. 공통 오류는 code/requestId를 반환하며 내부 credential/DSN은 응답하지 않는다.

## 다른 방법과 선택 근거

OFFSET은 새 행 삽입 때 페이지 중복을 만들 수 있다. 안정적인 키 기반 cursor가 이력 탐색에 적합하다. 런타임 Pydantic+Zod는 TypeScript 타입만 사용하는 대안과 달리 실제 네트워크 JSON도 검증한다.

## 개발 중 문제와 해결·남은 한계

숫자형 검색을 제한 없이 정수로 바꾸면 DB 범위를 넘을 수 있어 PR 번호 검색을 제한했다. legacy verification:null과 프런트 계약 불일치는 nullish 허용으로 해결했다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

# D44 — GitHub 실제 결과 수집

DOCX 3-04 대응 · 기록일 2026-11-23 (KST). D번호는 기록 순서이며 실제 하루의 작업량이나 확정 일정이 아닙니다.

## 작업

GitHub REST의 run/attempt별 artifact를 pull하고 manifest를 검증한다.

## 완료 기준과 실제 확인

실제 GitHub artifact→DB 저장과 403/429/5xx·위조·압축 폭탄·부분 파일·만료·크기 제한·signed URL credential 분리를 확인한다. 새 PR 실행 증거는 통합 검수에 별도로 기록한다.

[실제 수집](../docs/backend/evidence/live-import.json), `test_pull_never_forwards_credential_to_signed_download`, archive/expired metadata 테스트. 실제 사용 credential의 최소 권한 여부는 서버 코드가 검증할 수 없어 운영자가 별도 확인해야 한다.

## 어떤 기능을 어떻게 구현했는가

`github.py`, `artifacts.py`에서 API로 repo ID/run/attempt/head/workflow를 확인한 뒤 SHA256과 manifest를 대조한다. ZIP은 메모리에서 제한해 읽고 디스크에 풀지 않는다. 별도의 무인증 HTTP client로 허용된 signed download host에만 접근한다.

## 다른 방법과 선택 근거

Webhook은 로컬 서버의 수신 주소·서명 검증·인터넷 노출을 요구한다. outbound pull은 localhost에서도 동작하고 Actions read 권한으로 제한할 수 있다. checksum은 무결성 확인이며 저장소 접근 권한의 대체물이 아니다.

## 개발 중 문제와 해결·남은 한계

리다이렉트 다운로드에 API Authorization을 전달할 위험을 별도 client로 없앴다. 만료/잘못된 크기 metadata는 다운로드 전에 실패 처리한다. 수집 실패를 검사 passed로 바꾸지 않는다.

[3차 운영 가이드](../docs/backend/README.md) · [통합 검수 결과](../docs/backend-validation.md)

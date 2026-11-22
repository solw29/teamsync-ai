# TeamSync Review Dashboard

```bash
npm ci --cache /workspace/.cache/npm
npm run dev
npm run build
npm test
```

Routes: /dashboard, /pulls/:id, /evaluation, /data. Default data is an anonymized real D10 measurement bundle. Import actual `docs/report-example.json` in Data to see commit links and original code. Imports are validated and kept in memory; refresh returns to demo data.

Static deployment: choose `web/` as project root, build `npm run build`, output `dist/`. Set history fallback to index.html (Vercel config included). No environment secrets are needed. Do not copy private reports into public/ or dist/. Deployment has not been performed automatically.

## 작업과 완료 기준

네 화면의 조회·검색·필터·정렬·JSON 가져오기·코드 복사·평가 표시와 v1/v2 호환을 제공한다. 완료 기준은 `npm test`, `npm run build`, 실제 Chromium의 import/링크/복사/모바일/오류 경로 검증이다. 현재 2차 기준 frontend 9개와 빌드·브라우저 검증을 통과했다. 외부 호스팅과 API 모드는 이 기록에서 완료로 표시하지 않는다.

## 구현 방법과 선택 근거

React Hooks와 Router로 작은 읽기 전용 SPA를 구성하고 Zod adapter가 version별 입력을 검증한다. Redux나 브라우저의 직접 GitHub/LLM 호출 대신 단일 bundle import를 택한 이유는 초기 서버·credential 저장 없이 실제 결과를 보여주기 위해서다. CSS bar는 소수 범주의 실측 분포를 표현하기에 충분했고, chart engine 간 성능 비교를 수행한 것은 아니다. API 이력·페이지네이션은 별도 DataSource로 연결할 후속 범위다.

## 개발 중 문제와 해결

npm 캐시 권한 오류는 workspace cache로 해결했다. Evidence 탭 추가 시 모바일 overflow는 flex-wrap/overflow-wrap으로 수정하고 390px에서 검증했다. 원본에 PR 제목·세부 시간이 없던 항목은 발명하지 않고 미측정/사례 ID로 표시했다. 구체적인 오류와 증거는 `../docs/react-test-report.md`, `../docs/phase2/validation.md`, D11~D20/D38 README에 있다. 공개 데모와 imported 결과를 구분하며, 이 UI 검증은 전체 접근성 인증이나 외부 배포 검증을 대신하지 않는다.

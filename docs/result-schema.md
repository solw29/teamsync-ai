# Result bundle 1.0

정본: `web/src/schema.ts`의 Zod 스키마. Exporter: `teamsync/export_report.py`.

- `schemaVersion`: 정확히 `1.0`. 다른 버전은 거부합니다.
- `analyses[]`: 고유 id, repository, prNumber, prTitle, headSha, runId, analyzedAt(ISO), githubUrl(HTTPS GitHub PR URL 또는 null), status.
- status: passed / failed / running / partial. 검사 상태는 passed / failed / running / error / skipped / not_run / environment_error / missing_input.
- checks: ruffStatus, pytestStatus, errorSummary(null 허용). duration은 초 단위 또는 null.
- review: status, summary, findings(file,line,evidence,suggestion,locationVerified,adjudication). adjudication은 unreviewed / confirmed / false_positive. 위치만으로 confirmed로 바꾸지 않습니다.
- tests: target, code, purpose, executionStatus, failureReason(null 허용). 원본에 상세 오류가 없으면 임의로 만들지 않습니다.
- discordRequestStatus: passed / error / not_configured. HTTP 성공과 사용자 수신 확인은 다릅니다.
- execution: 이름과 상태. 원본에 없는 단계 시간은 만들지 않습니다.
- evaluation: 실제 집계 결과 또는 null. 개별 PR의 검사 통과와 버그/수정 양쪽 비교 결과를 혼동하지 않습니다.

실제 D10 변환 예시는 `docs/report-example.json`, 익명화 데모는 `web/public/demo.json`입니다. 후자는 공개용만 사용하세요.

```bash
python -m teamsync.export_report --evidence 1107_D6/live-evidence --output artifacts/report.json
python -m teamsync.export_report --evidence 1107_D6/live-evidence --output web/public/demo.json --public
```

새 Actions에서 evidence 구조를 생성한 후 위 명령과 `actions/upload-artifact@v4`의 path: artifacts/report.json을 별도 단계로 연결할 수 있습니다. 기존 production workflow에는 아직 자동 export 단계를 주입하지 않았습니다. 이 어댑터는 보존된 D10 evidence를 입력으로 받으며, 개별 잡의 원시 artifact만으로 PR 메타데이터·게시 결과를 추측하지 않습니다.

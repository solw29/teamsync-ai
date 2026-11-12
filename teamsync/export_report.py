"""Read-only adapter for preserved D10 evidence; never executes imported code."""
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal['passed', 'failed', 'running', 'error', 'skipped', 'not_run', 'environment_error', 'missing_input']


class Finding(BaseModel):
    file: str
    line: int = Field(gt=0)
    evidence: str
    suggestion: str
    locationVerified: bool
    adjudication: Literal['unreviewed', 'confirmed', 'false_positive']


class Checks(BaseModel):
    ruffStatus: Status
    pytestStatus: Status
    errorSummary: str | None


class ReviewData(BaseModel):
    status: Status
    summary: str
    findings: list[Finding]


class Draft(BaseModel):
    target: str
    code: str
    purpose: str
    executionStatus: Status
    failureReason: str | None


class Item(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    repository: str
    prNumber: int = Field(gt=0)
    prTitle: str
    headSha: str
    runId: int
    analyzedAt: str
    githubUrl: str | None
    status: Literal['passed', 'failed', 'running', 'partial']
    checks: Checks
    review: ReviewData
    tests: list[Draft]
    discordRequestStatus: str
    duration: float | None
    execution: list[dict]


class Report(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schemaVersion: Literal['1.0']
    analyses: list[Item]
    evaluation: dict | None = None


def export(root: Path, public: bool = False) -> Report:
    analyses = []
    for folder in sorted(root.glob('S*-*')):
        if not folder.is_dir():
            continue
        read = lambda name, folder=folder: json.loads((folder / f'{name}.json').read_text())
        publication, analysis, diff = read('publication'), read('analysis'), read('diff')
        checks, generated = read('checks'), read('generated')
        raw = analysis.get('review') or {}
        findings = []
        for finding in raw.get('findings', []):
            valid = finding['line'] in diff['positions'].get(finding['file'], [])
            findings.append({**finding, 'locationVerified': valid, 'adjudication': 'unreviewed'})
        tests = [{**draft, 'executionStatus': generated[i]['status'] if i < len(generated) else 'not_run',
                  'failureReason': None} for i, draft in enumerate(raw.get('tests', []))]
        repository = publication['comment_url'].split('github.com/')[1].split('/pull/')[0]
        statuses = {c['status'] for c in checks}
        status = 'partial' if analysis['status'] != 'passed' else 'failed' if statuses & {'failed', 'error'} else 'passed'
        url = publication['comment_url'].split('#')[0]
        summary = raw.get('summary', '')
        if public:
            repository, url, summary = 'demo/python-project', None, '익명화한 실제 시드 PR 분석 결과입니다. 원본 코드와 로그는 포함하지 않습니다.'
            findings = [{**f, 'file': 'example.py', 'evidence': '원본 근거는 공개 데모에서 제거했습니다.',
                         'suggestion': '실제 결과 파일을 가져오면 원본 제안을 확인할 수 있습니다.',
                         'locationVerified': False} for f in findings]
            tests = [{**t, 'target': 'sample_function', 'code': '# 공개 데모에서 원본 테스트 코드를 제거했습니다.',
                      'purpose': '시드 계약 검증'} for t in tests]
        checkmap = {c['name']: c['status'] for c in checks}
        analyses.append(Item(id=folder.name, repository=repository, prNumber=publication['pr'],
            prTitle=f'{folder.name} · 시드 계약 평가', headSha='' if public else publication['head_sha'],
            runId=publication['run_id'], analyzedAt=publication['comment_updated_at'], githubUrl=url,
            status=status, checks={'ruffStatus': checkmap.get('ruff', 'not_run'),
                'pytestStatus': checkmap.get('pytest', 'not_run'), 'errorSummary': None},
            review={'status': analysis['status'], 'summary': summary, 'findings': findings}, tests=tests,
            discordRequestStatus='passed' if publication['body'].endswith('Discord: passed') else 'error',
            duration=publication.get('run_to_comment_seconds'),
            execution=[{'name': 'Pipeline', 'status': publication['conclusion']}]))
    evaluation = json.loads((root / 'summary.json').read_text()) if (root / 'summary.json').exists() else None
    # Only allow measured scalar metrics into the public-facing contract.
    metrics = None if evaluation is None else {key: evaluation[key] for key in (
        'cases', 'bug_review_cases', 'fixed_false_positives_code_inspected', 'valid_locations',
        'published_locations', 'fixed_execution_without_environment_error', 'fixed_passed_tests',
        'total_same_draft_tests', 'cases_with_detecting_test', 'same_draft_test_outcomes')}
    return Report(schemaVersion='1.0', analyses=analyses, evaluation=metrics)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--public', action='store_true')
    args = parser.parse_args()
    result = export(args.evidence, args.public)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2))


if __name__ == '__main__':
    main()

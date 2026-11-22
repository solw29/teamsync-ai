"""Phase-2 stages. Secret stages only consume JSON; they never import target code."""
import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .analyze import analyze
from .cli import read, write
from .collect_diff import collect
from .export_report import Item
from .llm_router import bounded_input, route
from .notebooks import inspect_source
from .phase2_config import load_policy
from .phase2_schema import (
    Evidence,
    Requirement,
    RunIdentity,
    RunReport,
    Usage,
    save_report,
)
from .repository_index import git, impact
from .requirements import judge, load_contracts
from .run_generated_tests import execute
from .schema import Review
from .structured_checks import collect_checks, gate


def load(folder, name, fallback=None):
    path = folder / f'{name}.json'
    return read(path) if path.exists() else fallback


def collect_stage(target, folder, policy, contracts):
    checks = collect_checks(str(target), policy)
    graph = impact(str(target), os.environ['BASE_SHA'], os.environ['HEAD_SHA'], policy)
    graph['notebooks'] = []
    for change in graph['changes']:
        path = change['new']
        if path.endswith('.ipynb') and change['status'] != 'D':
            if not policy.notebookStatic:
                graph['notebooks'].append({'file': path, 'status': 'skipped', 'reason': 'notebook_static_disabled'})
                continue
            spec = os.environ['HEAD_SHA'] + ':' + path
            size = int(git(str(target), 'cat-file', '-s', spec))
            result = inspect_source(git(str(target), 'cat-file', 'blob', spec)) if size <= 200000 else {'status': 'environment_error', 'reason': 'size_limit'}
            graph['notebooks'].append({'file': path, **result})
    diff = collect(os.environ['BASE_SHA'], os.environ['HEAD_SHA'], str(target))
    requirements, evidence = judge(contracts, graph['head'], checks)
    for name, value in {'checks': checks, 'diff': diff, 'impact': graph,
                        'requirements': [r.model_dump() for r in requirements],
                        'evidence': [e.model_dump() for e in evidence],
                        'contracts': [c.model_dump() for c in contracts]}.items():
        write(folder / f'{name}.json', value)


def analyze_stage(folder, policy):
    diff, checks = load(folder, 'diff', {'lines': [], 'positions': {}}), load(folder, 'checks', [])
    requirements = [Requirement.model_validate(r) for r in load(folder, 'requirements', [])]
    routing = route(diff, checks, requirements, policy)
    write(folder / 'routing.json', routing)
    if routing['call']:
        result = analyze(bounded_input(diff, policy), checks, contracts=load(folder, 'contracts', []),
                         max_tokens=policy.maxOutputTokens, max_input_chars=policy.maxInputChars)
    else:
        result = {'status': 'skipped', 'review': None, 'reason': routing['reason'],
                  'usage': {'calls': 0, 'inputTokens': None, 'outputTokens': None, 'estimatedCost': None}}
    write(folder / 'analysis.json', result)


def report_stage(folder, output, policy, event):
    pr = event['pull_request']
    repo = event['repository']
    identity = RunIdentity(repositoryId=repo['id'], fullName=repo['full_name'], prNumber=pr['number'],
        baseSha=pr['base']['sha'], headSha=pr['head']['sha'], workflowId=os.environ.get('GITHUB_WORKFLOW_ID', 'unavailable:' + os.environ.get('GITHUB_WORKFLOW_REF', 'local-fixture')),
        runId=int(os.environ['GITHUB_RUN_ID']), runAttempt=int(os.environ.get('GITHUB_RUN_ATTEMPT', '1')),
        observedAt=datetime.now(UTC))
    checks = load(folder, 'checks', [])
    analysis = load(folder, 'analysis', {'status': 'not_run', 'review': None})
    generated = load(folder, 'generated', [])
    diff = load(folder, 'diff', {'positions': {}})
    raw = analysis.get('review') or {}
    findings = []
    for f in raw.get('findings', []):
        # Independently verify even if an artifact claims a finding is valid.
        findings.append({**f, 'locationVerified': f['line'] in diff['positions'].get(f['file'], []),
                         'adjudication': 'unreviewed'})
    tests = []
    for i, draft in enumerate(raw.get('tests', [])):
        outcome = generated[i] if i < len(generated) else {'status': 'not_run', 'reason': 'not_executed'}
        tests.append({**draft, 'executionStatus': outcome['status'], 'failureReason': outcome.get('reason')})
    by_name = {c['name']: c for c in checks}
    requirements = [Requirement.model_validate(r) for r in load(folder, 'requirements', [])]
    required_pass = gate(checks, policy.requiredChecks + (['coverage'] if policy.coverageTarget else [])) and not any(r.status == 'violated' for r in requirements)
    partial = analysis['status'] in ('error', 'missing_input', 'not_run') or (policy.generatedTests and (not generated or any(g['status'] != 'passed' for g in generated)))
    status = 'failed' if not required_pass else 'partial' if partial else 'passed'
    item = Item(id=f"{identity.repositoryId}-{identity.runId}-{identity.runAttempt}", repository=identity.fullName,
        prNumber=identity.prNumber, prTitle=pr['title'], headSha=identity.headSha, runId=identity.runId,
        analyzedAt=identity.observedAt.isoformat().replace('+00:00', 'Z'), githubUrl=f'https://github.com/{identity.fullName}/pull/{identity.prNumber}',
        status=status, checks={'ruffStatus': by_name.get('ruff', {}).get('status', 'not_run'),
                              'pytestStatus': by_name.get('pytest', {}).get('status', 'not_run'), 'errorSummary': None},
        review={'status': analysis['status'], 'summary': raw.get('summary', analysis.get('reason', '')),
                'findings': findings}, tests=tests,
        discordRequestStatus=load(folder, 'notifications', {}).get('discord', 'not_configured'), duration=None,
        execution=[{'name': c['name'], 'status': c['status']} for c in checks])
    usage = analysis.get('usage') or {'calls': int(load(folder, 'routing', {}).get('call', False))}
    contract_version = hashlib.sha256(json.dumps(load(folder, 'contracts', []), sort_keys=True).encode()).hexdigest()
    config_version = hashlib.sha256((policy.version + contract_version).encode()).hexdigest()[:16]
    report = RunReport(contractVersion=contract_version, model=analysis.get('model'), promptVersion=hashlib.sha256(Path(__file__).with_name('prompts').joinpath('review.txt').read_bytes()).hexdigest(), configVersion=config_version, identity=identity, analysis=item, requirements=requirements,
        evidence=[Evidence.model_validate(e) for e in load(folder, 'evidence', [])], checkDetails=checks,
        testEvidence=[{'index': i, 'requirementIds': [c['id'] for c in load(folder, 'contracts', [])
                         if c['symbol'].split('.')[-1] == t['target'].split('.')[-1]],
                         'expectationValidation': 'not_independently_verified'} for i, t in enumerate(tests)],
        impact=load(folder, 'impact', {}), routing=load(folder, 'routing', {}), usage=Usage.model_validate(usage),
        warnings=load(folder, 'impact', {}).get('warnings', []) +
                 (['Missing checks artifact'] if not checks else []) +
                 (['LLM skipped does not establish semantic correctness'] if analysis['status'] == 'skipped' else []))
    save_report(report, output)
    return required_pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['collect', 'analyze', 'execute', 'report', 'gate'])
    parser.add_argument('--target', type=Path, default=Path('target'))
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts'))
    parser.add_argument('--output', type=Path, default=Path('report-output'))
    parser.add_argument('--policy', type=Path, default=Path('teamsync-policy.json'))
    parser.add_argument('--contracts', type=Path, default=Path('teamsync-requirements.json'))
    args = parser.parse_args()
    policy = load_policy(args.policy)
    if args.stage == 'collect':
        collect_stage(args.target, args.artifacts, policy, load_contracts(args.contracts))
    elif args.stage == 'analyze':
        analyze_stage(args.artifacts, policy)
    elif args.stage == 'execute':
        analysis = load(args.artifacts, 'analysis', {})
        if not policy.generatedTests:
            generated = [{'target': t['target'], 'status': 'not_run', 'reason': 'generated_tests_opt_in_required'} for t in (analysis.get('review') or {}).get('tests', [])]
        elif os.environ.get('TEAMSYNC_ISOLATED_CONTAINER') != '1':
            generated = [{'target': t['target'], 'status': 'not_run', 'reason': 'restricted_container_required'} for t in (analysis.get('review') or {}).get('tests', [])]
        elif analysis.get('review'):
            generated = execute(Review.model_validate(analysis['review']), str(args.target), strict=True, contracts=load(args.artifacts, 'contracts', load(args.artifacts, 'input', {}).get('contracts', [])))
        else:
            generated = []
        write(args.output / 'generated.json', generated)
    elif args.stage == 'report':
        report_stage(args.artifacts, args.output, policy, json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()))
    else:
        checks = load(args.artifacts, 'checks', [])
        requirements = load(args.artifacts, 'requirements', [])
        passed = gate(checks, policy.requiredChecks + (['coverage'] if policy.coverageTarget else [])) and not any(r['status'] == 'violated' for r in requirements)
        raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()

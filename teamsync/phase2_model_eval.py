"""Manually dispatched, single-call model evaluation on known synthetic contracts."""
import argparse
import ast
import hashlib
import os
from pathlib import Path

from .analyze import analyze
from .cli import read, write
from .evaluate import SEEDS, classify
from .phase2_config import Policy
from .structured_checks import run_tool


def prepare(case, root):
    selected = next(s for s in SEEDS if s[0] == case)
    _, buggy, fixed, assertion = selected
    function = ast.parse(buggy).body[0].name
    tests = f'from sample import {function}\n\n\ndef test_contract():\n    {assertion}\n'
    for version, code in [('buggy', buggy), ('fixed', fixed)]:
        path = root/version
        path.mkdir(parents=True, exist_ok=True)
        (path/'sample.py').write_text(ast.unparse(ast.parse(code))+'\n')
        (path/'test_contract.py').write_text(tests)
        for file in path.iterdir():
            file.chmod(0o644)
        path.chmod(0o755)
    source = (root/'buggy/sample.py').read_text()
    lines = [{'file': 'sample.py', 'line': i+1, 'code': line} for i, line in enumerate(source.splitlines())]
    checks = [run_tool(name, str(root/'buggy')) for name in ('ruff', 'pytest')]
    write(root/'input.json', {'case': case, 'diff': {'lines': lines, 'positions': {'sample.py': list(range(1,len(lines)+1))}},
          'checks': checks, 'contracts': [{'id': 'REQ-'+case, 'description': assertion, 'symbol': 'sample.'+function,
                                         'testIds': ['test_contract::test_contract'], 'assertions': [assertion]}]})
    write(root/'runner-policy.json', {'generatedTests': True})


def generate(root):
    data = read(root/'input.json')
    policy = Policy(llmMode='always')
    result = analyze(data['diff'], data['checks'], contracts=data['contracts'],
                     max_tokens=policy.maxOutputTokens, max_input_chars=policy.maxInputChars)
    write(root/'analysis.json', result)


def summarize(root):
    data, analysis = read(root/'input.json'), read(root/'analysis.json')
    buggy, fixed = read(root/'result-buggy/generated.json'), read(root/'result-fixed/generated.json')
    comparisons = []
    for i, (b, f) in enumerate(zip(buggy, fixed, strict=True)):
        comparisons.append({'index': i, 'target': b.get('target'), 'buggy': b['status'], 'fixed': f['status'],
                            'classification': classify(b['status'], f['status'])})
    prompt = Path(__file__).parent/'prompts/review.txt'
    write(root/'model-evaluation.json', {'case': data['case'], 'source': 'new_model_drafts_same_code_on_both_versions',
          'runId': os.environ.get('GITHUB_RUN_ID'), 'toolSHA': os.environ.get('GITHUB_SHA'),
          'model': analysis.get('model') or analysis.get('requestedModel'), 'requestedModel': analysis.get('requestedModel'), 'promptSHA256': hashlib.sha256(prompt.read_bytes()).hexdigest(),
          'configVersion': Policy(llmMode='always').version, 'analysisStatus': analysis['status'],
          'usage': analysis.get('usage'), 'tests': comparisons,
          'limitation': 'Synthetic known contract, not independent holdout or general accuracy. No estimated costs without prices.'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare','generate','summarize'])
    parser.add_argument('--case', choices=[s[0] for s in SEEDS])
    parser.add_argument('--root', type=Path, default=Path('artifacts/model'))
    args = parser.parse_args()
    if args.stage == 'prepare':
        if args.case is None:
            parser.error('--case required')
        prepare(args.case,args.root)
    elif args.stage == 'generate':
        generate(args.root)
    else:
        summarize(args.root)


if __name__ == '__main__':
    main()

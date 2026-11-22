"""Offline rule/router comparison. Does NOT measure new LLM accuracy or spend."""
import json
import platform
import sys
import tempfile
from pathlib import Path

from .evaluate import SEEDS
from .llm_router import route
from .phase2_config import Policy
from .requirements import Contract, judge
from .structured_checks import run_tool


def evaluate():
    rows = []
    with tempfile.TemporaryDirectory(prefix='teamsync-phase2-eval-') as temp:
        root = Path(temp)
        for case, buggy, fixed, assertion in SEEDS:
            function = buggy.split('def ')[1].split('(')[0]
            tests = f'from sample import {function}\n\n\ndef test_contract():\n    {assertion}\n'
            # Fresh processes and fresh paths, never two independent LLM drafts.
            (root / 'test_contract.py').write_text(tests)
            results = []
            for version, code in [('buggy', buggy), ('fixed', fixed)]:
                path = root / (case + '-' + version)
                path.mkdir()
                (path / 'sample.py').write_text(code + '\n')
                (path / 'test_contract.py').write_text(tests)
                checks = [run_tool('pytest', str(path))]
                graph = {'symbols': [{'name': 'sample.' + function, 'file': 'sample.py', 'line': 1}], 'warnings': [], 'calls': [{'caller': 'test_contract.test_contract', 'target': 'sample.'+function}]}
                contract = Contract(id='REQ-' + case, description=assertion, symbol='sample.' + function,
                                    testIds=['test_contract::test_contract'])
                requirements, _ = judge([contract], graph, checks)
                diff = {'lines': [{'file': 'sample.py', 'line': 1, 'code': code}]}
                results.append({'version': version, 'execution': checks[0]['status'],
                                'judgement': requirements[0].status,
                                'alwaysWouldCall': route(diff, checks, requirements, Policy(llmMode='always'))['call'],
                                'selectiveWouldCall': route(diff, checks, requirements, Policy())['call']})
            rows.append({'case': case, 'source': 'handwritten_contract_not_model_output', 'results': results})
    return {'scope': '6 cleaned synthetic contract pairs, deterministic checks only', 'cases': rows,
            'environment': {'python': platform.python_version(), 'platform': sys.platform},
            'toolVersion': '0.2.0', 'configVersion': Policy().version, 'actualLLMCalls': 0, 'llmDetectionChange': None, 'tokenSavings': None,
            'limitation': 'Would-call decisions are not measured API savings or new model accuracy. Holdout not sent to a model.'}


if __name__ == '__main__':
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))

import json
import subprocess
from pathlib import Path

import pytest

from teamsync.draft_quality import check_draft
from teamsync.llm_router import bounded_input, route
from teamsync.notebooks import inspect
from teamsync.phase2_config import Policy, load_policy
from teamsync.repository_index import impact, index
from teamsync.requirements import Contract, judge, load_contracts
from teamsync.structured_checks import classify, gate, run_tool


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', *args], cwd=root, text=True).strip()


@pytest.fixture
def history(tmp_path):
    git(tmp_path, 'init', '-q')
    (tmp_path / 'lib.py').write_text('def helper():\n    return 1\n')
    (tmp_path / 'caller.py').write_text('from lib import helper\ndef main():\n    return helper()\n\ndef dynamic(x):\n    return x.method()\n')
    git(tmp_path, 'add', '.'); git(tmp_path, 'commit', '-qm', 'base')
    base = git(tmp_path, 'rev-parse', 'HEAD')
    git(tmp_path, 'mv', 'lib.py', 'renamed.py')
    git(tmp_path, 'commit', '-qam', 'rename')
    return tmp_path, base, git(tmp_path, 'rev-parse', 'HEAD')


def test_base_callers_survive_rename(history):
    root, base, head = history
    result = impact(root, base, head, Policy())
    assert result['changes'][0]['status'].startswith('R')
    assert 'caller.main' in result['affectedSymbols']
    assert result['head']['unresolved']
    assert 'renamed.helper' in result['changedSymbols']


def test_limits_and_revision_validation(history):
    root, base, _ = history
    limited = index(root, base, Policy(maxFileBytes=1))
    assert limited['warnings'] and not limited['symbols']
    with pytest.raises(ValueError):
        index(root, '--help', Policy())


def contract():
    return Contract(id='REQ-ZERO', description='Return None for zero', symbol='lib.helper', testIds=['test_contract::test_zero'])


@pytest.mark.parametrize('passed,failed,status', [([], [], 'unverifiable'),
    (['test_contract::test_zero'], [], 'satisfied'), ([], ['test_contract::test_zero'], 'violated')])
def test_contract_requires_exact_executed_test(passed, failed, status):
    graph = {'symbols': [{'name': 'lib.helper', 'file': 'lib.py', 'line': 1}], 'warnings': [], 'calls': [{'caller':'test_contract.test_zero','target':'lib.helper'}]}
    results, evidence = judge([contract()], graph, [{'name': 'pytest', 'passedTests': passed, 'failedTests': failed}])
    assert results[0].status == status
    assert set(results[0].evidenceIds) <= {e.id for e in evidence}


def test_truncated_index_cannot_satisfy():
    graph = {'symbols': [{'name': 'lib.helper', 'file': 'lib.py', 'line': 1}], 'warnings': ['limited']}
    results, _ = judge([contract()], graph, [{'name': 'pytest', 'passedTests': ['test_contract::test_zero']}])
    assert results[0].status == 'unverifiable'


@pytest.mark.parametrize('code,reason', [(1, 'assertion_failure'), (2, 'collection_error'), (5, 'no_tests')])
def test_check_failure_causes(code, reason):
    assert classify('pytest', code, '')[1] == reason


def test_real_no_tests_and_collection_error(tmp_path):
    result = run_tool('pytest', str(tmp_path))
    assert result['status'] == 'environment_error' and result['reason'] == 'no_tests'
    (tmp_path / 'test_bad.py').write_text('invalid syntax @@@')
    assert run_tool('pytest', str(tmp_path))['reason'] == 'collection_error'


def test_real_test_identity_and_failure(tmp_path):
    (tmp_path / 'test_contract.py').write_text('def test_ok():\n    assert True\n\ndef test_zero():\n    assert False\n')
    result = run_tool('pytest', str(tmp_path))
    assert result['passedTests'] == ['test_contract::test_ok']
    assert result['failedTests'] == ['test_contract::test_zero']
    assert not gate([result], ['pytest'])
    assert not gate([], ['pytest'])


def test_timeout_kills_test_process(tmp_path):
    (tmp_path / 'test_slow.py').write_text('import time\ndef test_wait():\n    time.sleep(5)\n')
    result = run_tool('pytest', str(tmp_path), timeout=.4)
    assert result['reason'] == 'timeout'


def test_router_does_not_equate_green_checks_with_semantic_coverage():
    diff = {'lines': [{'file': 'a.py', 'line': 1, 'code': 'def a(): pass'}]}
    checks = [{'name': 'pytest', 'status': 'passed'}]
    assert route(diff, checks, [], Policy())['call']
    assert not route(diff, checks, [], Policy(llmMode='off'))['call']
    assert route(diff, checks, [], Policy(llmMode='off'))['semanticCoverage'] == 'not_assessed'
    missing = [{'reason': 'tool_missing'}]
    assert not route(diff, missing, [], Policy())['call']
    bounded = bounded_input({'lines': diff['lines'] * 100}, Policy(maxInputChars=100))
    assert bounded['truncated'] and len(json.dumps(bounded['lines'])) <= 100


@pytest.mark.parametrize('code,reason', [
    ('def test_x(): assert True', 'standalone_target_import_missing'),
    ('from lib import helper\nimport socket\ndef test_x(): assert helper()', 'disallowed_import'),
    ('from lib import helper\ndef test_x(): open("secret")\n', 'disallowed_call'),
])
def test_draft_rejection(code, reason):
    assert reason in check_draft(code, 'helper')


def test_valid_standalone_draft():
    assert not check_draft('from lib import helper\ndef test_contract():\n    assert helper() is None', 'helper')


def test_notebook_opt_in_and_magic(tmp_path):
    file = tmp_path / 'sample.ipynb'
    file.write_text(json.dumps({'cells': [{'cell_type': 'code', 'source': ['%matplotlib inline'], 'outputs': ['do not retain']},
                                       {'cell_type': 'code', 'source': 'def f(): pass'}]}))
    assert inspect(file)['status'] == 'skipped'
    result = inspect(file, True)
    assert result['execution'] == 'not_run' and result['cells'][0]['status'] == 'unresolved'
    assert 'do not retain' not in json.dumps(result)


def test_policy_and_contract_validation(tmp_path):
    path = tmp_path / 'policy.json'; path.write_text('{"requiredChecks":["shell"]}')
    with pytest.raises(ValueError): load_policy(path)
    path.write_text('[{"id":"REQ-1","description":"contract","symbol":"a.f"},{"id":"REQ-1","description":"contract","symbol":"a.f"}]')
    with pytest.raises(ValueError): load_contracts(path)


def test_tool_missing_is_not_passed(monkeypatch, tmp_path):
    monkeypatch.setattr('teamsync.structured_checks.importlib.util.find_spec', lambda _: None)
    assert run_tool('pyright', str(tmp_path))['reason'] == 'tool_missing'


def test_model_input_limit_prevents_request(monkeypatch):
    from teamsync.analyze import analyze

    monkeypatch.setenv('LLM_API_KEY', 'test-placeholder')
    result = analyze({'lines': [{'code': 'x'*1000}]}, [], max_input_chars=100)
    assert result['error'] == 'model_input_limit_exceeded' and result['usage']['calls'] == 0


def test_pyright_and_coverage_optional_tools(tmp_path):
    pytest.importorskip('pyright')
    pytest.importorskip('pytest_cov')
    from teamsync.structured_checks import collect_checks

    (tmp_path/'sample.py').write_text('def answer() -> int:\n    return "wrong"\n')
    typed = run_tool('pyright', str(tmp_path))
    assert typed['status'] == 'failed' and typed['diagnostics']
    (tmp_path/'sample.py').write_text('def answer():\n    return 42\n')
    (tmp_path/'test_sample.py').write_text('from sample import answer\n\n\ndef test_answer():\n    assert answer() == 42\n')
    results = collect_checks(str(tmp_path), Policy(coverageTarget='sample', coverageMinimum=90))
    coverage = next(c for c in results if c['name'] == 'coverage')
    assert coverage['measured'] == 100 and coverage['status'] == 'passed'


def test_holdout_not_silently_judged():
    from teamsync.requirements import Contract, judge

    cases = json.loads(Path('tests/fixtures/phase2/holdout.json').read_text())
    graph = {'symbols': [], 'warnings': []}
    for case in cases:
        results, _ = judge([Contract(**case)], graph, [])
        assert results[0].status == 'unverifiable'


def test_model_evaluation_prepares_contract_and_summarizes_same_drafts(tmp_path):
    from teamsync.phase2_model_eval import prepare, summarize

    prepare('S01', tmp_path)
    data = json.loads((tmp_path/'input.json').read_text())
    assert data['contracts'][0]['description'] == 'assert safe_divide(1,0) is None'
    assert data['checks'][1]['status'] == 'failed'
    (tmp_path/'analysis.json').write_text(json.dumps({'status':'passed','review':None,'usage':{'calls':1}}))
    for version,status in [('buggy','failed'),('fixed','passed')]:
        directory=tmp_path/f'result-{version}'
        directory.mkdir()
        (directory/'generated.json').write_text(json.dumps([{'target':'safe_divide','status':status}]))
    summarize(tmp_path)
    result=json.loads((tmp_path/'model-evaluation.json').read_text())
    assert result['tests'][0]['classification'] == 'detected'


def test_green_unconnected_test_is_unverifiable():
    graph = {'symbols':[{'name':'lib.helper','file':'lib.py','line':1}], 'warnings':[], 'calls':[]}
    result,_=judge([contract()],graph,[{'name':'pytest','passedTests':['test_contract::test_zero']}])
    assert result[0].status == 'unverifiable'

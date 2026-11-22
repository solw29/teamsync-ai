"""Fixed commands, bounded output; only run target code on trusted disposable runners."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .phase2_config import Policy


def classify(name, code, output):
    if code == 0:
        return 'passed', None
    if name == 'pytest':
        reasons = {1: 'assertion_failure', 2: 'collection_error', 3: 'internal_error',
                   4: 'usage_error', 5: 'no_tests'}
        return ('failed' if code == 1 else 'environment_error'), reasons.get(code, 'process_error')
    return ('failed', 'diagnostics') if code == 1 else ('environment_error', 'process_error')


def run_tool(name: str, cwd: str, timeout=120, coverage: str | None = None):
    started = time.monotonic()
    if importlib.util.find_spec(name) is None:
        return {'name': name, 'status': 'environment_error', 'reason': 'tool_missing',
                'exit_code': None, 'duration': 0, 'summary': '', 'diagnostics': []}
    options = {'ruff': ['check', '.', '--output-format=json'],
               'pytest': ['-q', '--rootdir=.'], 'pyright': ['--outputjson']}[name]
    if name == 'pytest' and coverage:
        options += [f'--cov={coverage}', '--cov-report=json:coverage.json']
    with tempfile.TemporaryDirectory(prefix='teamsync-check-') as directory, tempfile.TemporaryFile(mode='w+') as stream:
        junit = Path(directory) / 'junit.xml'
        coverage_path = Path(directory) / 'coverage.json'
        if name == 'pytest':
            options += [f'--junitxml={junit}']
            if coverage:
                options = [f'--cov-report=json:{coverage_path}' if o == '--cov-report=json:coverage.json' else o for o in options]
        process = subprocess.Popen([sys.executable, '-m', name, *options], cwd=cwd,
                                   stdout=stream, stderr=stream, start_new_session=True)
        reason = None
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            reason, code = 'timeout', None
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        stream.seek(0, 2)
        length = stream.tell()
        stream.seek(max(0, length - 6000))
        output = stream.read()
        passed_tests, failed_tests = [], []
        if name == 'pytest' and junit.exists() and junit.stat().st_size < 2_000_000:
            try:
                for case in ET.parse(junit).getroot().iter('testcase'):
                    identity = case.get('classname', '') + '::' + case.get('name', '')
                    if case.find('failure') is not None:
                        failed_tests.append(identity)
                    elif case.find('error') is None and case.find('skipped') is None:
                        passed_tests.append(identity)
            except ET.ParseError:
                reason = 'invalid_junit'
        measured = None
        if coverage_path.exists() and coverage_path.stat().st_size < 2_000_000:
            try:
                measured = json.loads(coverage_path.read_text())['totals']['percent_covered']
            except (ValueError, KeyError):
                pass
    status, classified = classify(name, code, output) if reason is None else ('environment_error', reason)
    diagnostics = []
    if name in ('ruff', 'pyright') and length <= 6000:
        try:
            raw = json.loads(output)
            diagnostics = raw if name == 'ruff' else raw.get('generalDiagnostics', [])
        except (ValueError, AttributeError):
            if code == 0:
                status, classified = 'environment_error', 'invalid_output'
    return {'name': name, 'status': status, 'reason': reason or classified, 'exit_code': code,
            'duration': round(time.monotonic() - started, 3), 'summary': output,
            'diagnostics': diagnostics, 'outputTruncated': length > 6000,
            'passedTests': passed_tests, 'failedTests': failed_tests, 'coveragePercent': measured}


def collect_checks(cwd: str, policy: Policy):
    results = [run_tool('ruff', cwd), run_tool('pytest', cwd, coverage=policy.coverageTarget)]
    results.append(run_tool('pyright', cwd) if policy.pyright else
                   {'name': 'pyright', 'status': 'skipped', 'reason': 'disabled', 'diagnostics': []})
    if policy.coverageTarget:
        measured = next(c for c in results if c['name'] == 'pytest').get('coveragePercent')
        results.append({'name': 'coverage', 'status': 'environment_error' if measured is None else
                        'passed' if measured >= policy.coverageMinimum else 'failed',
                        'target': policy.coverageTarget, 'minimum': policy.coverageMinimum, 'measured': measured})
    return results


def gate(checks, required):
    by_name = {c['name']: c for c in checks}
    return bool(required) and all(by_name.get(name, {}).get('status') == 'passed' for name in required)

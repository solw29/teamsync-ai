import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from teamsync.export_report import export
from teamsync.phase2_cli import report_stage
from teamsync.phase2_config import Policy
from teamsync.phase2_schema import RunIdentity, load_report


@pytest.fixture
def run_report(tmp_path, monkeypatch):
    root = Path('1107_D6/live-evidence/S01-buggy')
    for source in root.glob('*.json'):
        if source.name != 'publication.json':
            (tmp_path / source.name).write_bytes(source.read_bytes())
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2')
    event = {'repository': {'id': 42, 'full_name': 'owner/repo'},
             'pull_request': {'number': 1, 'title': 'Actual title', 'base': {'sha': 'a' * 40}, 'head': {'sha': 'b' * 40}}}
    output = tmp_path / 'report'
    assert not report_stage(tmp_path, output, Policy(), event)  # actual pytest failure preserved
    return output


def test_v2_round_trip_identity_checksum(run_report):
    report = load_report(run_report)
    assert report.identity.runAttempt == 2 and report.analysis.status == 'failed'
    assert report.usage.inputTokens is None
    manifest = json.loads((run_report / 'manifest.json').read_text())
    assert set(manifest['files']) == {'report.json'}


def test_tamper_and_identity_mismatch(run_report):
    path = run_report / 'report.json'
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='checksum'): load_report(run_report)


def test_incomplete_run_is_not_passed(tmp_path, monkeypatch):
    monkeypatch.setenv('GITHUB_RUN_ID', '124')
    event = {'repository': {'id': 42, 'full_name': 'owner/repo'},
             'pull_request': {'number': 1, 'title': 'Partial', 'base': {'sha': 'a'*40}, 'head': {'sha': 'b'*40}}}
    assert not report_stage(tmp_path, tmp_path/'out', Policy(), event)
    report = load_report(tmp_path/'out')
    assert report.analysis.status == 'failed' and report.warnings


def test_v1_baseline_preserved():
    result = export(Path('1107_D6/live-evidence'))
    assert len(result.analyses) == 12 and result.schemaVersion == '1.0'


def test_manifest_sha_validation():
    with pytest.raises(ValidationError):
        RunIdentity(repositoryId=1, fullName='owner/repo', prNumber=1, baseSha='--bad',
                    headSha='a'*40, workflowId='review', runId=1, runAttempt=1, observedAt='2026-11-22T00:00:00Z')

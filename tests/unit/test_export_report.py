from pathlib import Path

from teamsync.export_report import export


def test_real_evidence_export():
    report = export(Path('1107_D6/live-evidence'))
    assert len(report.analyses) == 12
    assert report.evaluation['valid_locations'] == 15
    assert all(a.githubUrl.startswith('https://github.com/') for a in report.analyses)


def test_public_export_removes_code_and_metadata():
    report = export(Path('1107_D6/live-evidence'), public=True)
    data = report.model_dump_json()
    assert 'solw29' not in data
    assert 'from demo_s01 import' not in data
    assert all(a.githubUrl is None and not a.headSha for a in report.analyses)

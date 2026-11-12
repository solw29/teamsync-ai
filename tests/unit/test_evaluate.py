import pytest

from teamsync.evaluate import classify, evaluate


@pytest.mark.parametrize("buggy,fixed,expected", [
    ("failed", "passed", "detected"), ("passed", "passed", "missed"),
    ("failed", "failed", "manual_review"), ("passed", "failed", "unstable_or_environment"),
])
def test_classification(buggy, fixed, expected):
    assert classify(buggy, fixed) == expected


def test_six_seed_pairs():
    rows = evaluate()
    assert len(rows) == 6
    assert all(row["classification"] == "detected" for row in rows)

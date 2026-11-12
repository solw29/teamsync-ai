"""Tests for the shared check result model."""

import pytest
from pydantic import ValidationError

from teamsync import CheckResult, CheckStatus


@pytest.mark.parametrize("status", list(CheckStatus))
def test_check_result_serializes_status(status: CheckStatus) -> None:
    result = CheckResult(name="pytest", status=status, summary="3 tests passed")

    assert result.model_dump(mode="json") == {
        "name": "pytest",
        "status": status.value,
        "summary": "3 tests passed",
        "exit_code": None,
    }


def test_check_result_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        CheckResult(name="", status=CheckStatus.PASSED)

"""Shared result types for local and GitHub Actions checks."""

from enum import Enum

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    """Outcome of a single automated check."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class CheckResult(BaseModel):
    """Structured check outcome that can later be included in PR reports."""

    name: str = Field(min_length=1)
    status: CheckStatus
    summary: str = ""
    exit_code: int | None = None

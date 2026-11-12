from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Finding(StrictModel):
    file: str = Field(min_length=1, max_length=300)
    line: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(min_length=1, max_length=2000)


class TestDraft(StrictModel):
    target: str = Field(min_length=1, max_length=300)
    code: str = Field(min_length=1, max_length=10000)
    purpose: str = Field(min_length=1, max_length=1000)


class Review(StrictModel):
    summary: str = Field(max_length=4000)
    findings: list[Finding] = Field(max_length=20)
    tests: list[TestDraft] = Field(max_length=5)

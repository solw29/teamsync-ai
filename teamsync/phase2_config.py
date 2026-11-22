"""Policy comes from the trusted tool/base checkout, never the PR head."""
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Policy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schemaVersion: Literal['1.0'] = '1.0'
    requiredChecks: list[str] = Field(default_factory=lambda: ['ruff', 'pytest'])
    pyright: bool = False
    coverageTarget: str | None = None
    coverageMinimum: float = Field(default=0, ge=0, le=100)
    maxFiles: int = Field(default=100, ge=1, le=1000)
    maxFileBytes: int = Field(default=100000, ge=1, le=1000000)
    maxTotalBytes: int = Field(default=2000000, ge=1, le=10000000)
    notebookStatic: bool = False
    generatedTests: bool = False
    llmMode: str = Field(default='selective', pattern=r'^(off|always|selective)$')
    maxLLMCalls: int = Field(default=1, ge=0, le=1)
    maxInputChars: int = Field(default=24000, ge=100, le=50000)
    maxOutputTokens: int = Field(default=6000, ge=100, le=6000)

    @property
    def version(self):
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:16]


def load_policy(path: Path) -> Policy:
    if not path.exists():
        return Policy()
    if path.is_symlink() or path.stat().st_size > 100000:
        raise ValueError('Policy file rejected')
    data = json.loads(path.read_text())
    policy = Policy.model_validate(data)
    if set(policy.requiredChecks) - {'ruff', 'pytest', 'pyright'}:
        raise ValueError('Unknown required check')
    if 'pyright' in policy.requiredChecks and not policy.pyright:
        raise ValueError('Required Pyright must be enabled')
    return policy

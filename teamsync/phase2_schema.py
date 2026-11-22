"""Versioned run evidence. Execution, requirement judgement and evidence are distinct."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .export_report import Item


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class RunIdentity(Strict):
    repositoryId: int = Field(gt=0)
    fullName: str = Field(pattern=r'^[\w.-]+/[\w.-]+$')
    prNumber: int = Field(gt=0)
    baseSha: str = Field(pattern=r'^[0-9a-f]{40}$')
    headSha: str = Field(pattern=r'^[0-9a-f]{40}$')
    workflowId: str = Field(min_length=1)
    runId: int = Field(gt=0)
    runAttempt: int = Field(gt=0)
    observedAt: datetime


class Evidence(Strict):
    id: str
    kind: Literal['contract', 'symbol', 'call', 'check', 'test', 'unresolved']
    file: str
    line: int = Field(ge=0)
    detail: str


class Requirement(Strict):
    id: str
    description: str
    status: Literal['satisfied', 'violated', 'unverifiable']
    evidenceIds: list[str]
    reason: str


class Usage(Strict):
    calls: int = Field(ge=0)
    inputTokens: int | None = Field(default=None, ge=0)
    outputTokens: int | None = Field(default=None, ge=0)
    estimatedCost: float | None = Field(default=None, ge=0)


class RunReport(Strict):
    schemaVersion: Literal['2.0'] = '2.0'
    toolVersion: str = '0.2.0'
    configVersion: str
    identity: RunIdentity
    analysis: Item
    requirements: list[Requirement]
    evidence: list[Evidence]
    checkDetails: list[dict]
    impact: dict
    routing: dict
    usage: Usage
    warnings: list[str]
    testEvidence: list[dict] = Field(default_factory=list)
    model: str | None = None
    promptVersion: str = 'unrecorded'

    @model_validator(mode='after')
    def consistent(self):
        identity = self.identity
        item = self.analysis
        if (item.repository != identity.fullName or item.prNumber != identity.prNumber
                or item.headSha != identity.headSha or item.runId != identity.runId):
            raise ValueError('Embedded analysis identity mismatch')
        ids = {e.id for e in self.evidence}
        if len(ids) != len(self.evidence) or len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError('Duplicate evidence or requirement ID')
        if any(set(r.evidenceIds) - ids for r in self.requirements):
            raise ValueError('Unknown evidence reference')
        return self



class Manifest(Strict):
    schemaVersion: Literal['2.0'] = '2.0'
    toolVersion: str
    configVersion: str
    identity: RunIdentity
    files: dict[Literal['report.json'], str]


def save_report(report: RunReport, output: Path) -> Manifest:
    evidence_ids = {e.id for e in report.evidence}
    if any(set(r.evidenceIds) - evidence_ids for r in report.requirements):
        raise ValueError('Unknown evidence reference')
    output.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump_json(indent=2).encode()
    (output / 'report.json').write_bytes(payload)
    manifest = Manifest(toolVersion=report.toolVersion, configVersion=report.configVersion,
                        identity=report.identity, files={'report.json': hashlib.sha256(payload).hexdigest()})
    (output / 'manifest.json').write_text(manifest.model_dump_json(indent=2))
    return manifest


def load_report(root: Path) -> RunReport:
    for name in ('manifest.json', 'report.json'):
        path = root / name
        if path.is_symlink() or path.stat().st_size > 5_000_000:
            raise ValueError('Report path or size rejected')
    manifest = Manifest.model_validate_json((root / 'manifest.json').read_text())
    payload = (root / 'report.json').read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest.files['report.json']:
        raise ValueError('Report checksum mismatch')
    report = RunReport.model_validate_json(payload)
    if (report.identity != manifest.identity or report.toolVersion != manifest.toolVersion
            or report.configVersion != manifest.configVersion):
        raise ValueError('Manifest identity mismatch')
    ids = {e.id for e in report.evidence}
    if any(set(r.evidenceIds) - ids for r in report.requirements):
        raise ValueError('Unresolved evidence reference')
    return report


def schema_file(path: Path):
    path.write_text(json.dumps(RunReport.model_json_schema(), indent=2))

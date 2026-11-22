from typing import Literal

from pydantic import BaseModel

from teamsync.export_report import Item


class Analysis(Item):
    verification: dict | None = None


class RunsResponse(BaseModel):
    items: list[Analysis]
    nextCursor: str | None
    source: Literal["api"]
    lastSyncedAt: str | None
    syncError: str | None


class DetailResponse(BaseModel):
    analysis: Analysis
    schemaVersion: str
    runAttempt: int | None
    githubStatus: str
    githubConclusion: str | None
    collectionStatus: Literal["available", "unavailable", "partial"]
    collectedAt: str


class StatsResponse(BaseModel):
    counts: dict[str, int]
    total: int
    asOf: str
    days: int
    version: int
    cacheSource: Literal["hit", "miss", "database_fallback"]


class RepositoryResponse(BaseModel):
    id: str
    externalId: int
    fullName: str
    workflowIds: list[int]


class RepositoriesResponse(BaseModel):
    items: list[RepositoryResponse]


class SessionResponse(BaseModel):
    username: str
    csrfToken: str


class JobEventResponse(BaseModel):
    status: str
    reason: str | None
    at: str


class JobResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "retrying", "succeeded", "failed", "cancelled"]
    attempts: int
    reason: str | None
    runId: int
    runAttempt: int
    createdAt: str
    updatedAt: str
    nextRetryAt: str | None
    finishedAt: str | None
    events: list[JobEventResponse] = []


class ErrorDetail(BaseModel):
    code: str
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorDetail

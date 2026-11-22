"""Outbound-only GitHub connector. No workflow dispatch/rerun or secret writes."""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .artifacts import MAX_ARCHIVE, parse_archive
from .errors import SyncError


class GitHubClient:
    def __init__(self, settings, transport=None):
        token = (
            os.environ.get(settings.github_token_env, "")
            if settings.github_token_env
            else ""
        )
        if not token:
            try:
                token = Path(settings.github_token_file).read_text().strip()
            except OSError:
                raise SyncError("github_credential_missing") from None
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20,
            follow_redirects=False,
            transport=transport,
        )
        self.transport = transport

    def close(self):
        self.client.close()

    @staticmethod
    def check(response):
        status = response.status_code
        if status == 429 or (
            status == 403 and response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            delay = response.headers.get("Retry-After", "60")
            raise SyncError(
                "github_rate_limit",
                True,
                min(int(delay) if delay.isdigit() else 60, 3600),
            )
        if status >= 500:
            raise SyncError("github_unavailable", True)
        if status in (401, 403):
            raise SyncError("github_permission_denied")
        if status >= 400:
            raise SyncError("github_resource_unavailable")

    def get(self, path, params=None):
        if not path.startswith("/") or path.startswith("//"):
            raise SyncError("invalid_github_path")
        try:
            response = self.client.get(path, params=params)
            self.check(response)
            if response.is_redirect:
                raise SyncError("github_unexpected_redirect")
            data = response.json()
            if not isinstance(data, dict):
                raise SyncError("github_invalid_response")
            return data
        except httpx.HTTPError:
            raise SyncError("github_transport", True) from None
        except ValueError:
            raise SyncError("github_invalid_response") from None

    def repository(self, repo):
        info = self.get(f"/repositories/{repo.external_id}")
        if info.get("id") != repo.external_id or not re.fullmatch(
            r"[\w.-]+/[\w.-]+", info.get("full_name", "")
        ):
            raise SyncError("repository_identity_mismatch")
        return info

    def sync(self, repo, run_id, attempt):
        info = self.repository(repo)
        path = "/repos/" + info["full_name"] + f"/actions/runs/{run_id}"
        run = self.get(path + f"/attempts/{attempt}")
        if (
            run.get("id") != run_id
            or run.get("run_attempt") != attempt
            or run.get("workflow_id") not in repo.workflow_ids
        ):
            raise SyncError("github_run_identity_mismatch")
        if run.get("status") != "completed":
            raise SyncError("analysis_not_finished", True, 30)
        candidates = []
        for page in range(1, 4):
            artifacts = self.get(
                path + "/artifacts", {"per_page": 100, "page": page}
            ).get("artifacts", [])
            candidates.extend(
                a
                for a in artifacts
                if a.get("name")
                in (
                    f"teamsync-report-{run_id}-{attempt}",
                    f"phase2-run-{run_id}-{attempt}",
                )
            )
            if len(artifacts) < 100:
                break
        else:
            raise SyncError("artifact_list_limit")
        if not candidates:
            raise SyncError("artifact_unavailable", True)
        if len(candidates) != 1:
            raise SyncError("artifact_ambiguous")
        artifact = candidates[0]
        size = artifact.get("size_in_bytes")
        if (
            artifact.get("expired")
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or size > MAX_ARCHIVE
        ):
            raise SyncError("artifact_expired_or_size_limit")
        data = self.download(
            "/repos/" + info["full_name"] + f"/actions/artifacts/{artifact['id']}/zip"
        )
        report = parse_archive(data, repo, run)
        return report, run, info["full_name"]

    def download(self, path):
        try:
            with self.client.stream("GET", path) as response:
                self.check(response)
                if response.status_code == 200:
                    blocks = []
                    size = 0
                    for block in response.iter_bytes():
                        size += len(block)
                        if size > MAX_ARCHIVE:
                            raise SyncError("artifact_size_limit")
                        blocks.append(block)
                    return b"".join(blocks)
                url = response.headers.get("location", "")
            # Never forward Authorization to signed download destinations.
            with httpx.Client(
                timeout=30, follow_redirects=False, transport=self.transport
            ) as download:
                for _ in range(3):
                    parsed = urlparse(url)
                    host = parsed.hostname or ""
                    if (
                        parsed.scheme != "https"
                        or parsed.username
                        or parsed.port not in (None, 443)
                        or not (
                            host in ("github.com", "api.github.com")
                            or host.endswith(
                                (
                                    ".blob.core.windows.net",
                                    ".githubusercontent.com",
                                    ".actions.githubusercontent.com",
                                )
                            )
                        )
                    ):
                        raise SyncError("artifact_destination_rejected")
                    with download.stream("GET", url) as stream:
                        self.check(stream)
                        if stream.is_redirect:
                            url = stream.headers.get("location", "")
                            continue
                        chunks, size = [], 0
                        for block in stream.iter_bytes():
                            size += len(block)
                            if size > MAX_ARCHIVE:
                                raise SyncError("artifact_size_limit")
                            chunks.append(block)
                        return b"".join(chunks)
        except httpx.HTTPError:
            raise SyncError("artifact_transport", True) from None
        raise SyncError("artifact_redirect_limit")

"""Bounded in-memory ZIP reader. A checksum is never treated as authorization."""

import hashlib
import io
import json
import stat
import zipfile

from teamsync.phase2_schema import Manifest, RunReport

from .errors import SyncError

MAX_REPORT = 5_000_000
MAX_ARCHIVE = 10_000_000


def parse_archive(payload, repo, api_run):
    if len(payload) > MAX_ARCHIVE:
        raise SyncError("artifact_size_limit")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            names = [i.filename for i in entries]
            if sorted(names) != ["manifest.json", "report.json"] or len(names) != len(
                set(names)
            ):
                raise SyncError("artifact_paths_or_duplicates")
            if any(stat.S_ISLNK(i.external_attr >> 16) for i in entries):
                raise SyncError("artifact_symlink")
            if sum(i.file_size for i in entries) > MAX_REPORT or any(
                i.file_size > 100 * max(i.compress_size, 1) for i in entries
            ):
                raise SyncError("artifact_expansion_limit")
            manifest = Manifest.model_validate_json(archive.read("manifest.json"))
            data = archive.read("report.json")
            if hashlib.sha256(data).hexdigest() != manifest.files["report.json"]:
                raise SyncError("artifact_checksum_mismatch")
            report = RunReport.model_validate_json(data)
    except SyncError:
        raise
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, RuntimeError):
        raise SyncError("artifact_invalid") from None
    identity = report.identity
    actual_repo = api_run.get("repository", {})
    if (
        identity != manifest.identity
        or report.toolVersion != manifest.toolVersion
        or report.configVersion != manifest.configVersion
        or repo.external_id != actual_repo.get("id")
        or identity.repositoryId != repo.external_id
        or identity.runId != api_run.get("id")
        or identity.runAttempt != api_run.get("run_attempt")
        or identity.headSha != api_run.get("head_sha")
        or identity.workflowId != str(api_run.get("workflow_id"))
        or api_run.get("workflow_id") not in repo.workflow_ids
    ):
        raise SyncError("manifest_api_identity_mismatch")
    # Repository ID authorizes the source; names may have changed since the run.
    report._source_sha256 = hashlib.sha256(data).hexdigest()
    report._source_payload = json.loads(data)
    return report

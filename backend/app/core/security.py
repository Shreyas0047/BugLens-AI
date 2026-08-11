"""Security guards for untrusted repository input.

All rules here treat uploaded/cloned content as hostile:
path traversal (zip-slip), zip bombs, oversized uploads, oversized repos.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, status

GITHUB_URL_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ENTRY_SYMLINK = 0o170000
_SYMLINK_MODE = 0o120000


class IngestionError(HTTPException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a github.com URL. Raises on anything else."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != "github.com":
        raise IngestionError("Only GitHub repository URLs are supported (github.com/owner/repo)")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise IngestionError("GitHub URL must look like https://github.com/owner/repo")
    owner, repo = parts[0], parts[1]
    repo = repo.removesuffix(".git")
    if not GITHUB_URL_RE.match(f"{owner}/{repo}"):
        raise IngestionError("Invalid GitHub owner/repo in URL")
    return owner, repo


def safe_zip_entry(info: zipfile.ZipInfo, limits: dict) -> None:
    """Reject a single zip entry if it is unsafe."""
    if info.is_dir():
        return
    name = info.filename
    norm = PurePosixPath(name)
    if norm.is_absolute() or ".." in norm.parts:
        raise IngestionError(f"Zip entry uses an unsafe path: {name!r}")
    if info.external_attr >> 16 & _ENTRY_SYMLINK == _SYMLINK_MODE:
        raise IngestionError(f"Zip entry is a symlink (not allowed): {name!r}")
    if info.file_size > limits["max_file_mb"] * 1024 * 1024:
        raise IngestionError(f"Zip entry too large: {name!r} ({info.file_size} bytes)")
    if info.compress_size and info.file_size / info.compress_size > limits["max_zip_ratio"]:
        raise IngestionError(f"Zip entry suspiciously compressed (possible zip bomb): {name!r}")


def enforce_workspace_limits(root: Path, limits: dict) -> None:
    """Walk an extracted/cloned workspace and enforce total size/file-count limits."""
    total = 0
    count = 0
    for path in root.rglob("*"):
        if path.is_file():
            count += 1
            total += path.stat().st_size
            if count > limits["max_file_count"]:
                raise IngestionError(
                    f"Too many files ({count}); limit is {limits['max_file_count']}"
                )
            if total > limits["max_repo_mb"] * 1024 * 1024:
                raise IngestionError(
                    f"Repository exceeds size limit of {limits['max_repo_mb']} MB expanded"
                )


def resolve_within(root: Path, relative_name: str) -> Path:
    """Resolve a member path inside root, refusing anything that escapes it."""
    target = (root / relative_name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise IngestionError(f"Path escapes workspace: {relative_name!r}")
    return target

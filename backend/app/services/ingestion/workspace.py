"""Per-run isolated workspaces for repository analysis."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.config import get_settings


def create_workspace(repository_id: int, run_id: int) -> Path:
    settings = get_settings()
    base = settings.workspace_dir.resolve()
    base.mkdir(parents=True, exist_ok=True)
    workspace = base / f"repo-{repository_id}-run-{run_id}-{uuid.uuid4().hex[:8]}"
    workspace.mkdir(parents=True)
    return workspace


def cleanup_workspace(path: Path) -> None:
    import shutil

    if path.exists():
        shutil.rmtree(path, ignore_errors=True)

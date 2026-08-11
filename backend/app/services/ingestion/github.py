"""GitHub repository ingestion via shallow clone with timeouts and env scrubbing."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import get_settings
from app.core.security import enforce_workspace_limits


class CloneError(Exception):
    pass


def clone_github(url: str, dest: Path) -> None:
    settings = get_settings()
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(Path.home()),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GCM_INTERACTIVE": "Never",
    }
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:limit=1m", "--quiet", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=settings.clone_timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise CloneError(f"Clone timed out after {settings.clone_timeout_seconds}s") from exc
    except OSError as exc:
        raise CloneError(f"Failed to run git: {exc}") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        raise CloneError(f"git clone failed: {detail}")

    try:
        enforce_workspace_limits(dest, _limits())
    except Exception:
        import shutil

        shutil.rmtree(dest, ignore_errors=True)
        raise


def _limits() -> dict:
    s = get_settings()
    return {
        "max_file_mb": s.max_file_mb,
        "max_file_count": s.max_file_count,
        "max_repo_mb": s.max_repo_mb,
    }

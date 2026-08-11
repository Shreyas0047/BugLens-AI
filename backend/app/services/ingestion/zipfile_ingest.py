"""ZIP project extraction with zip-slip / zip-bomb / size guards."""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.config import get_settings
from app.core.security import (
    IngestionError,
    enforce_workspace_limits,
    resolve_within,
    safe_zip_entry,
)


def extract_zip(zip_path: Path, dest: Path) -> None:
    settings = get_settings()
    limits = {
        "max_file_mb": settings.max_file_mb,
        "max_zip_ratio": settings.max_zip_ratio,
        "max_expanded_mb": settings.max_expanded_mb,
        "max_file_count": settings.max_file_count,
    }

    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            entries = zf.infolist()
            if len(entries) > limits["max_file_count"]:
                raise IngestionError(
                    f"Zip contains {len(entries)} entries; limit is {limits['max_file_count']}"
                )
            expanded = sum(i.file_size for i in entries if not i.is_dir())
            if expanded > limits["max_expanded_mb"] * 1024 * 1024:
                raise IngestionError(
                    f"Zip expands to {expanded // (1024 * 1024)} MB; "
                    f"limit is {limits['max_expanded_mb']} MB"
                )
            for info in entries:
                safe_zip_entry(info, limits)
                if info.is_dir():
                    continue
                target = resolve_within(dest, info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    while chunk := src.read(1024 * 256):
                        out.write(chunk)
    except zipfile.BadZipFile as exc:
        raise IngestionError("Uploaded file is not a valid ZIP archive") from exc

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

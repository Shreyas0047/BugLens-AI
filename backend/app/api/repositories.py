"""Repository endpoints: create from GitHub URL, upload ZIP, list, detail."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.db import get_db
from app.core.security import parse_github_url
from app.models.repository import AnalysisRun, Repository
from app.schemas.repository import RepositoryCreate, RepositoryOut, RepositoryWithRunOut
from app.services.jobs.enqueue import enqueue_analysis

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _derive_name(url: str | None, filename: str | None) -> str:
    if url:
        owner, repo = parse_github_url(url)
        return f"{owner}-{repo}"
    if filename:
        stem = Path(filename).stem
        return _SAFE_NAME_RE.sub("-", stem)[:80] or "uploaded-project"
    return "repository"


async def _create_repo_and_run(
    db: Session,
    *,
    source_type: str,
    url: str | None = None,
    name: str | None = None,
) -> tuple[Repository, AnalysisRun]:
    repo = Repository(
        name=name or _derive_name(url, None),
        source_type=source_type,
        url=url,
    )
    db.add(repo)
    db.flush()
    run = AnalysisRun(repository_id=repo.id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(repo)
    db.refresh(run)
    await enqueue_analysis(repo.id, run.id)
    return repo, run


@router.post("", response_model=RepositoryWithRunOut, status_code=202)
async def create_repository(payload: RepositoryCreate, db: Session = Depends(get_db)) -> dict:
    url = str(payload.url)
    parse_github_url(url)  # validate before touching anything
    repo, run = await _create_repo_and_run(db, source_type="github", url=url, name=payload.name)
    return {"repository": repo, "run": run}


@router.post("/upload", response_model=RepositoryWithRunOut, status_code=202)
async def upload_repository(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Only .zip files are accepted")

    repo = Repository(
        name=_derive_name(None, file.filename),
        source_type="zip",
        url=None,
    )
    db.add(repo)
    db.flush()
    run = AnalysisRun(repository_id=repo.id, status="pending")
    db.add(run)
    db.commit()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / f"repo-{repo.id}.zip"
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_zip_mb * 1024 * 1024:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Upload exceeds {settings.max_zip_mb} MB limit",
                    )
                out.write(chunk)
    except Exception:
        db.rollback()
        dest.unlink(missing_ok=True)
        db.delete(repo)
        db.commit()
        raise

    try:
        await enqueue_analysis(repo.id, run.id)
    except Exception:
        db.rollback()
        dest.unlink(missing_ok=True)
        db.delete(repo)
        db.commit()
        raise

    db.refresh(repo)
    db.refresh(run)
    return {"repository": repo, "run": run}


@router.get("", response_model=list[RepositoryOut])
def list_repositories(db: Session = Depends(get_db)) -> list[Repository]:
    return list(db.scalars(select(Repository).order_by(Repository.created_at.desc())).all())


@router.get("/{repository_id}", response_model=RepositoryOut)
def get_repository(repository_id: int, db: Session = Depends(get_db)) -> Repository:
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

"""Analysis pipeline: ordered stages executed by the ARQ worker.

Each stage updates run.stage / run.progress. Stages are added by later
phases (static analysis, NLP, risk, ...) by appending to STAGES.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from arq.connections import ArqRedis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.db import SessionLocal
from app.models.repository import AnalysisRun, Repository
from app.services.ingestion.github import clone_github
from app.services.ingestion.workspace import create_workspace
from app.services.ingestion.zipfile_ingest import extract_zip
from app.services.profiler.detect import profile_repository

StageFn = Callable[["StageContext", Session, Repository, AnalysisRun, Path], None]


class StageContext:
    def __init__(self, redis: ArqRedis) -> None:
        self.redis = redis


def _stage(name: str) -> Callable[[StageFn], tuple[str, StageFn]]:
    def register(fn: StageFn) -> tuple[str, StageFn]:
        return name, fn

    return register


@_stage("ingest")
def _ingest(
    ctx: StageContext, db: Session, repo: Repository, run: AnalysisRun, workspace: Path
) -> None:
    if repo.source_type == "github":
        clone_github(repo.url, workspace)
    elif repo.source_type == "zip":
        settings = get_settings()
        upload = settings.upload_dir / f"repo-{repo.id}.zip"
        if not upload.exists():
            raise FileNotFoundError(f"Uploaded archive missing: {upload}")
        extract_zip(upload, workspace)
    else:
        raise ValueError(f"Unknown source type: {repo.source_type}")


@_stage("profile")
def _profile(
    ctx: StageContext, db: Session, repo: Repository, run: AnalysisRun, workspace: Path
) -> None:
    profile = profile_repository(workspace)
    repo.languages_json = profile["languages"]
    repo.structure_json = {
        "manifests": profile["manifests"],
        "frameworks": profile["frameworks"],
        "top_level_dirs": profile["top_level_dirs"],
        "supported_languages": profile["supported_languages"],
    }


@_stage("analyze")
def _analyze(
    ctx: StageContext, db: Session, repo: Repository, run: AnalysisRun, workspace: Path
) -> None:
    from app.services.analysis.pipeline import run_analysis

    stored, tool_status = run_analysis(db, repo, run, workspace)
    run.error = None
    repo.structure_json = {
        **(repo.structure_json or {}),
        "tool_status": tool_status,
        "finding_count": stored,
    }


STAGES: list[tuple[str, StageFn]] = [
    _ingest,
    _profile,
    _analyze,
]


async def analyze_repository(ctx: dict, repository_id: int, run_id: int) -> None:
    redis: ArqRedis = ctx["redis"]
    db = SessionLocal()
    try:
        repo = db.get(Repository, repository_id)
        run = db.get(AnalysisRun, run_id)
        if repo is None or run is None:
            raise ValueError(f"Missing repository={repository_id} or run={run_id}")
        if run.status == "completed":
            return

        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.error = None
        db.commit()

        workspace = create_workspace(repo.id, run.id)
        repo.workspace_path = str(workspace)
        db.commit()

        stage_ctx = StageContext(redis)
        total = len(STAGES)
        try:
            for index, (name, fn) in enumerate(STAGES):
                run.stage = name
                run.progress = round(index / total * 100)
                db.commit()
                fn(stage_ctx, db, repo, run, workspace)
            run.stage = "finalize"
            run.progress = 100
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            db.commit()
        except Exception:
            run.stage = run.stage or "unknown"
            run.status = "failed"
            run.error = traceback.format_exc()[-3000:]
            run.finished_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()

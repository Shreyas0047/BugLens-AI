"""Analysis run endpoints: status polling + listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.repository import AnalysisRun, Repository
from app.schemas.repository import RunListOut, RunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])


class PredictOut(BaseModel):
    run_id: int
    updated: int
    model_version: str


@router.get("", response_model=list[RunListOut])
def list_runs(db: Session = Depends(get_db)) -> list[RunListOut]:
    rows = db.execute(
        select(AnalysisRun, Repository).join(Repository, AnalysisRun.repository_id == Repository.id)
    ).all()
    return [
        RunListOut(
            id=run.id,
            repository_id=repo.id,
            repository_name=repo.name,
            source_type=repo.source_type,
            status=run.status,
            stage=run.stage,
            progress=run.progress,
            error=run.error,
            created_at=run.started_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        for run, repo in rows
    ]


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/predict", response_model=PredictOut)
def predict_run(run_id: int, db: Session = Depends(get_db)) -> PredictOut:
    from app.services.analysis.predict import MODEL_VERSION, run_predict

    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Run has not completed yet")
    updated = run_predict(db, run_id)
    return PredictOut(run_id=run_id, updated=updated, model_version=MODEL_VERSION)

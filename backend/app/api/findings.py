"""Finding endpoints: filterable listing + stats for a run."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.finding import FileStat, Finding
from app.models.repository import AnalysisRun
from app.schemas.finding import (
    CategoryCount,
    FileStatOut,
    FindingListOut,
    FindingOut,
    FindingsStatsOut,
    SourceCount,
)

router = APIRouter(prefix="/api/runs", tags=["findings"])


def _get_run(run_id: int, db: Session) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/findings", response_model=FindingListOut)
def list_findings(
    run_id: int,
    db: Session = Depends(get_db),
    category: str | None = Query(None),
    source: str | None = Query(None),
    type: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    status: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> FindingListOut:
    _get_run(run_id, db)
    stmt = select(Finding).where(Finding.run_id == run_id)
    if category:
        stmt = stmt.where(Finding.category == category)
    if source:
        stmt = stmt.where(Finding.source == source)
    if type:
        stmt = stmt.where(Finding.type == type)
    if status:
        stmt = stmt.where(Finding.status == status)
    if min_confidence > 0:
        stmt = stmt.where(Finding.confidence >= min_confidence)
    if q:
        stmt = stmt.where(Finding.message.ilike(f"%{q}%") | Finding.file.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(Finding.confidence.desc(), Finding.id).limit(limit).offset(offset)
        ).all()
    )
    return FindingListOut(total=total, items=[FindingOut.model_validate(i) for i in items])


@router.get("/{run_id}/findings/stats", response_model=FindingsStatsOut)
def finding_stats(run_id: int, db: Session = Depends(get_db)) -> FindingsStatsOut:
    _get_run(run_id, db)
    by_category = [
        CategoryCount(category=row[0], count=row[1])
        for row in db.execute(
            select(Finding.category, func.count())
            .where(Finding.run_id == run_id)
            .group_by(Finding.category)
            .order_by(func.count().desc())
        ).all()
    ]
    by_source = [
        SourceCount(source=row[0], count=row[1])
        for row in db.execute(
            select(Finding.source, func.count())
            .where(Finding.run_id == run_id)
            .group_by(Finding.source)
            .order_by(func.count().desc())
        ).all()
    ]
    total = (
        db.scalar(select(func.count()).select_from(Finding).where(Finding.run_id == run_id)) or 0
    )
    high = (
        db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(Finding.run_id == run_id, Finding.confidence >= 0.8)
        )
        or 0
    )
    return FindingsStatsOut(
        total=total, by_category=by_category, by_source=by_source, high_confidence=high
    )


@router.get("/{run_id}/files", response_model=list[FileStatOut])
def list_files(run_id: int, db: Session = Depends(get_db)) -> list[FileStat]:
    _get_run(run_id, db)
    return list(
        db.scalars(
            select(FileStat)
            .where(FileStat.run_id == run_id)
            .order_by(FileStat.complexity.desc())
            .limit(500)
        ).all()
    )

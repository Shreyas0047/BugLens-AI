from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class FileStat(Base):
    """Per-run per-file statistics gathered during analysis."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="other")
    loc: Mapped[int] = mapped_column(Integer, default=0)
    complexity: Mapped[float] = mapped_column(Float, default=0.0)
    maintainability: Mapped[float | None] = mapped_column(Float)


class Finding(Base):
    """A single normalized static-analysis finding."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    # ast-custom|bandit|ruff|radon|eslint|ts-morph
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    # rule / test / code
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="CODE_SMELL")
    file: Mapped[str] = mapped_column(String(1024), nullable=False)
    line: Mapped[int] = mapped_column(Integer, default=0)
    column: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(4096), default="")
    description: Mapped[str] = mapped_column(String(2048), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_json: Mapped[dict | None] = mapped_column(JSON)
    # open|confirmed|false_positive|overridden  (review phase)
    status: Mapped[str] = mapped_column(String(24), default="open")
    # filled by the risk engine (Phase 5)
    risk_score: Mapped[float | None] = mapped_column(Float)
    severity_predicted: Mapped[str | None] = mapped_column(String(16))
    model_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

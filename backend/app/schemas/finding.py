from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

FindingStatus = Literal["open", "confirmed", "false_positive", "overridden"]


class FindingUpdate(BaseModel):
    status: FindingStatus


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    source: str
    type: str
    category: str
    file: str
    line: int
    column: int
    message: str
    description: str
    confidence: float
    evidence_json: dict | None
    status: str
    risk_score: float | None
    severity_predicted: str | None
    model_version: str | None
    created_at: datetime


class FindingListOut(BaseModel):
    total: int
    items: list[FindingOut]


class CategoryCount(BaseModel):
    category: str
    count: int


class SourceCount(BaseModel):
    source: str
    count: int


class FindingsStatsOut(BaseModel):
    total: int
    by_category: list[CategoryCount]
    by_source: list[SourceCount]
    high_confidence: int


class FileStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    language: str
    loc: int
    complexity: float
    maintainability: float | None

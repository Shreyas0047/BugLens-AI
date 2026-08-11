from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class RepositoryCreate(BaseModel):
    url: HttpUrl
    name: str | None = None


class RepositoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    url: str | None
    workspace_path: str | None
    languages_json: dict | None
    structure_json: dict | None
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    status: str
    stage: str | None
    progress: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class RepositoryWithRunOut(BaseModel):
    repository: RepositoryOut
    run: RunOut


class RunListOut(BaseModel):
    id: int
    repository_id: int
    repository_name: str
    source_type: str
    status: str
    stage: str | None
    progress: int
    error: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

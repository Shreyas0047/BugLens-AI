from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BUGLENS_", extra="ignore")

    app_name: str = "Bug Lens-Ai"
    debug: bool = True

    database_url: str = "sqlite:///./buglens.db"
    redis_url: str = "redis://localhost:6379"

    workspace_dir: Path = Path("./workspaces")
    upload_dir: Path = Path("./uploads")
    upload_keep_zip: bool = False

    # Ingestion limits (untrusted input guards)
    max_zip_mb: int = 50
    max_expanded_mb: int = 200
    max_repo_mb: int = 300
    max_file_mb: int = 10
    max_file_count: int = 20_000
    max_zip_ratio: float = 100.0
    clone_timeout_seconds: int = 120

    # Simple bearer auth; empty = disabled
    api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

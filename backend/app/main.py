from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis

from app.api import findings, repositories, runs
from app.config import get_settings
from app.core.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        redis_ok = False
        try:
            redis_ok = Redis.from_url(settings.redis_url).ping()
        except Exception:
            pass
        return {"status": "ok", "redis": redis_ok, "version": app.version}

    app.include_router(repositories.router)
    app.include_router(runs.router)
    app.include_router(findings.router)

    return app


app = create_app()

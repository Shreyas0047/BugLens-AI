from arq import create_pool
from arq.connections import RedisSettings

from app.config import get_settings


async def enqueue_analysis(repository_id: int, run_id: int) -> None:
    settings = get_settings()
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("analyze_repository", repository_id, run_id)
    finally:
        await pool.aclose()

"""ARQ worker entrypoint: uv run python -m workers.worker"""

import asyncio

from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

from app.config import get_settings
from app.services.jobs.tasks import analyze_repository


class WorkerSettings:
    functions = [analyze_repository]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 1
    job_timeout = 1800
    keep_result = 0


async def main() -> None:
    settings = WorkerSettings()
    pool = await create_pool(settings.redis_settings)
    worker = Worker(
        functions=settings.functions,
        redis_pool=pool,
        max_tries=settings.max_tries,
        job_timeout=settings.job_timeout,
        keep_result=settings.keep_result,
    )
    await worker.async_run()


if __name__ == "__main__":
    asyncio.run(main())

from collections.abc import Callable
from typing import Protocol

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError


class JobQueue(Protocol):
    def enqueue(self, job_id: str) -> None: ...


class InlineJobQueue:
    def __init__(self, execute: Callable[[str], None]) -> None:
        self.execute = execute

    def enqueue(self, job_id: str) -> None:
        self.execute(job_id)


class RQJobQueue:
    def __init__(self, redis_url: str, timeout_seconds: int) -> None:
        from redis import Redis
        from rq import Queue

        connection = Redis.from_url(redis_url)
        self.queue = Queue("generation", connection=connection, default_timeout=timeout_seconds)
        self.timeout_seconds = timeout_seconds

    def enqueue(self, job_id: str) -> None:
        self.queue.enqueue(
            "backend.app.workers.runner.execute_job",
            job_id,
            job_timeout=self.timeout_seconds,
        )


def create_job_queue(settings: Settings, inline_execute: Callable[[str], None]) -> JobQueue:
    if settings.queue_backend == "inline":
        return InlineJobQueue(inline_execute)
    if settings.queue_backend == "rq":
        return RQJobQueue(settings.redis_url, settings.job_default_timeout_seconds)
    raise ConfigurationError(f"Unsupported QUEUE_BACKEND: {settings.queue_backend}")

from redis import Redis
from rq import Queue, Worker

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("generation", connection=connection)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()

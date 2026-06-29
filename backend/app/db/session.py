from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings
from backend.app.db.base import Base

SessionFactory = sessionmaker[Session]


def ensure_sqlite_parent(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return
    Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(settings: Settings) -> Engine:
    ensure_sqlite_parent(settings.database_url)
    connect_args = (
        {"check_same_thread": False}
        if make_url(settings.database_url).get_backend_name() == "sqlite"
        else {}
    )
    return create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> SessionFactory:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    from backend.app.db import models  # noqa: F401

    Base.metadata.create_all(engine)

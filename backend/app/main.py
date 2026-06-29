from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1.router import router as api_router
from backend.app.application.jobs.queue import create_job_queue
from backend.app.application.jobs.service import JobService
from backend.app.caption_style_generator import OUTPUT_DIRECTORY as CAPTION_OUTPUT_DIRECTORY
from backend.app.core.config import Settings, get_settings
from backend.app.core.exception_handlers import register_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import RequestContextMiddleware
from backend.app.db.session import create_database_engine, create_session_factory, create_tables
from backend.app.workers.runner import execute_job


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    settings.generated_root.mkdir(parents=True, exist_ok=True)
    CAPTION_OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    if settings.app_env.casefold() in {"development", "local", "test", "testing"}:
        create_tables(engine)
    queue = create_job_queue(
        settings,
        partial(execute_job, session_factory=session_factory, settings=settings),
    )

    application = FastAPI(title=settings.app_name, debug=settings.debug)
    application.state.settings = settings
    application.state.db_engine = engine
    application.state.session_factory = session_factory
    application.state.job_service = JobService(session_factory, queue, settings)
    application.dependency_overrides[get_settings] = lambda: settings

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        RequestContextMiddleware,
        request_id_header=settings.request_id_header,
    )

    register_exception_handlers(application, settings)
    application.mount(
        "/generated",
        StaticFiles(directory=settings.generated_root),
        name="generated",
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    application.add_event_handler("shutdown", engine.dispose)
    return application


app = create_app()

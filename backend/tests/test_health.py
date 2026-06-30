from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import app, create_app


def test_app_can_be_imported() -> None:
    assert app.title


def test_public_route_contract_is_preserved() -> None:
    paths = set(app.openapi()["paths"])
    paths.update(path for route in app.routes if (path := getattr(route, "path", None)))
    assert {
        "/api/health",
        "/api/ready",
        "/api/provider/wavespeed/status",
        "/api/me",
        "/api/projects",
        "/api/projects/{project_id}",
        "/api/projects/{project_id}/members",
        "/api/projects/{project_id}/members/{user_id}",
        "/api/projects/{project_id}/jobs",
        "/api/audit",
        "/api/scripts/generate",
        "/api/voiceovers/generate",
        "/api/background-music/generate",
        "/api/art-style/generate",
        "/api/art-style/scenes/generate",
        "/api/videos/generate",
        "/api/scene-animations/generate",
        "/api/caption-style/generate",
        "/api/jobs/scripts/generate",
        "/api/jobs/voiceovers/generate",
        "/api/jobs/background-music/generate",
        "/api/jobs/art-style/generate",
        "/api/jobs/art-style/scenes/generate",
        "/api/jobs/scene-animations/generate",
        "/api/jobs/videos/generate",
        "/api/jobs/recover-stale",
        "/api/jobs/{job_id}/cancel",
        "/api/jobs/{job_id}",
        "/api/jobs",
        "/generated",
    } <= paths


def test_health_returns_ok_and_request_id() -> None:
    response = TestClient(app).get("/api/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request"


def test_readiness_returns_runtime_status(tmp_path) -> None:
    settings = Settings(_env_file=None, generated_root=tmp_path / "generated")
    response = TestClient(create_app(settings)).get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "environment": "development",
        "generated_root_exists": True,
    }
    assert response.headers["X-Request-ID"]


def test_unhandled_errors_are_safe_and_include_request_id(tmp_path) -> None:
    application = create_app(Settings(_env_file=None, generated_root=tmp_path / "generated"))

    @application.get("/test/unhandled", include_in_schema=False)
    def fail() -> None:
        raise RuntimeError("internal detail")

    response = TestClient(application, raise_server_exceptions=False).get(
        "/test/unhandled",
        headers={"X-Request-ID": "error-test"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected internal error occurred.",
            "request_id": "error-test",
        }
    }
    assert response.headers["X-Request-ID"] == "error-test"

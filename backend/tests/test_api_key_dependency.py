from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def test_missing_wavespeed_key_returns_consistent_error(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        wavespeed_api_key="",
        generated_root=tmp_path / "generated",
    )
    response = TestClient(create_app(settings)).post(
        "/api/scripts/generate",
        json={},
        headers={"X-Request-ID": "missing-key-test"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "configuration_error",
            "message": "Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
            "request_id": "missing-key-test",
        }
    }
    assert response.headers["X-Request-ID"] == "missing-key-test"

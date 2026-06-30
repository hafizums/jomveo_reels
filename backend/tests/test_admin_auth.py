import logging

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.security import is_valid_admin_key
from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError
from backend.app.db.models import GenerationJob
from backend.app.main import create_app
from backend.app.script_generator import ScriptRequest

ADMIN_KEY = "valid-test-admin-key"
BEARER_HEADERS = {"Authorization": f"Bearer {ADMIN_KEY}"}
FALLBACK_HEADERS = {"X-Admin-API-Key": ADMIN_KEY}


def _application(tmp_path, **overrides):
    values = {
        "app_env": "test",
        "admin_api_keys": [ADMIN_KEY],
        "generated_root": tmp_path / "generated",
        "local_storage_root": tmp_path / "generated",
        "database_url": f"sqlite:///{(tmp_path / 'auth.db').as_posix()}",
    }
    values.update(overrides)
    settings = Settings(_env_file=None, **values)
    return create_app(settings)


def test_provider_live_status_requires_admin_before_client_initialization(
    tmp_path, monkeypatch
) -> None:
    def unexpected_client(*_args, **_kwargs):
        raise AssertionError("unauthenticated live status initialized a provider client")

    monkeypatch.setattr(
        "backend.app.api.v1.provider.create_wavespeed_provider_client",
        unexpected_client,
    )
    response = TestClient(
        _application(
            tmp_path,
            allow_provider_live_checks=True,
            wavespeed_api_key="provider-secret",
        )
    ).get("/api/provider/wavespeed/status?live=true")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_required"


@pytest.mark.parametrize("headers", [BEARER_HEADERS, FALLBACK_HEADERS])
def test_provider_live_status_accepts_supported_admin_headers(tmp_path, headers) -> None:
    response = TestClient(_application(tmp_path)).get(
        "/api/provider/wavespeed/status?live=true",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["live_check_status"] == "disabled"


def test_provider_live_status_rejects_invalid_key_without_leaking_it(tmp_path) -> None:
    invalid_token = "invalid-secret-admin-token"
    response = TestClient(_application(tmp_path)).get(
        "/api/provider/wavespeed/status?live=true",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "auth_forbidden"
    assert invalid_token not in response.text


def test_job_recovery_requires_admin_and_accepts_valid_bearer(tmp_path) -> None:
    client = TestClient(_application(tmp_path))

    denied = client.post("/api/jobs/recover-stale")
    allowed = client.post("/api/jobs/recover-stale", headers=BEARER_HEADERS)

    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "auth_required"
    assert allowed.status_code == 200


def test_job_cancellation_requires_admin_and_preserves_response(tmp_path) -> None:
    application = _application(tmp_path)
    with application.state.session_factory() as session:
        job = GenerationJob(
            type="script.generate",
            status="queued",
            input_json=ScriptRequest().model_dump(mode="json"),
            max_attempts=3,
        )
        session.add(job)
        session.commit()
        job_id = job.id

    client = TestClient(application)
    denied = client.post(f"/api/jobs/{job_id}/cancel")
    allowed = client.post(f"/api/jobs/{job_id}/cancel", headers=BEARER_HEADERS)

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json() == {"job_id": job_id, "status": "cancelled"}


def test_job_creation_remains_unprotected(tmp_path) -> None:
    response = TestClient(_application(tmp_path)).post("/api/jobs/scripts/generate", json={})

    assert response.status_code == 200
    assert response.json()["type"] == "script.generate"


def test_disabled_admin_auth_returns_development_principal(tmp_path) -> None:
    response = TestClient(_application(tmp_path, admin_api_keys=[], admin_auth_enabled=False)).post(
        "/api/jobs/recover-stale"
    )

    assert response.status_code == 200


def test_production_rejects_enabled_admin_auth_without_keys(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        admin_auth_enabled=True,
        admin_api_keys=[],
        generated_root=tmp_path / "generated",
        local_storage_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'production.db').as_posix()}",
    )

    with pytest.raises(ConfigurationError, match="requires at least one"):
        create_app(settings)


def test_admin_key_comparison_uses_constant_time_helper(monkeypatch) -> None:
    compared = []

    def fake_compare(candidate, configured):
        compared.append((candidate, configured))
        return candidate == configured

    monkeypatch.setattr("backend.app.auth.security.secrets.compare_digest", fake_compare)

    assert is_valid_admin_key("second", ["first", "second"]) is True
    assert compared == [("second", "first"), ("second", "second")]


def test_auth_logs_do_not_contain_token(tmp_path, caplog) -> None:
    invalid_token = "never-log-this-admin-token"
    application = _application(tmp_path)
    caplog.set_level(logging.INFO)

    response = TestClient(application).post(
        "/api/jobs/recover-stale",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 403
    assert invalid_token not in caplog.text
    assert all(invalid_token not in str(record.__dict__) for record in caplog.records)

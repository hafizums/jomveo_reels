from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def _client(tmp_path, **overrides) -> TestClient:
    settings = Settings(
        _env_file=None,
        generated_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'status.db').as_posix()}",
        **overrides,
    )
    return TestClient(create_app(settings))


def test_provider_status_is_read_only_by_default(tmp_path, monkeypatch) -> None:
    def unexpected_client(*_args, **_kwargs):
        raise AssertionError("default status must not initialize a provider client")

    monkeypatch.setattr(
        "backend.app.api.v1.provider.create_wavespeed_provider_client",
        unexpected_client,
    )
    response = _client(tmp_path, wavespeed_api_key="do-not-expose").get(
        "/api/provider/wavespeed/status"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "wavespeed"
    assert body["mode"] == "sdk"
    assert body["sdk_available"] is True
    assert body["sdk_version"]
    assert body["api_key_configured"] is True
    assert body["chat_completions_mode"] == "legacy_http"
    assert body["live_check_status"] == "not_requested"
    assert "do-not-expose" not in response.text


def test_provider_live_status_requires_explicit_server_opt_in(tmp_path, monkeypatch) -> None:
    def unexpected_client(*_args, **_kwargs):
        raise AssertionError("disabled live checks must not initialize a client")

    monkeypatch.setattr(
        "backend.app.api.v1.provider.create_wavespeed_provider_client",
        unexpected_client,
    )
    response = _client(
        tmp_path,
        wavespeed_api_key="configured",
        admin_api_keys=["test-admin-key"],
    ).get(
        "/api/provider/wavespeed/status?live=true",
        headers={"Authorization": "Bearer test-admin-key"},
    )

    assert response.status_code == 200
    assert response.json()["live_check_status"] == "disabled"


def test_enabled_live_status_only_initializes_client(tmp_path, monkeypatch) -> None:
    class FakeClient:
        provider_mode = "sdk"

        def sdk_version(self) -> str:
            return "test-version"

    calls = []

    def fake_client(settings):
        calls.append(settings.wavespeed_api_key)
        return FakeClient()

    monkeypatch.setattr(
        "backend.app.api.v1.provider.create_wavespeed_provider_client",
        fake_client,
    )
    response = _client(
        tmp_path,
        wavespeed_api_key="ultra-secret-token",
        allow_provider_live_checks=True,
        admin_api_keys=["test-admin-key"],
    ).get(
        "/api/provider/wavespeed/status?live=true",
        headers={"Authorization": "Bearer test-admin-key"},
    )

    assert response.status_code == 200
    assert response.json()["live_check_status"] == "client_initialized"
    assert calls == ["ultra-secret-token"]
    assert "ultra-secret-token" not in response.text

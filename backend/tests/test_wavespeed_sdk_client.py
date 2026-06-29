from pathlib import Path
from typing import Any

import pytest
import wavespeed

from backend.app.art_style_generator import (
    ArtStyleRequest,
    ArtStyleResponse,
    generate_art_style_image,
)
from backend.app.background_music_generator import (
    BackgroundMusicRequest,
    generate_background_music,
)
from backend.app.core.config import Settings
from backend.app.core.errors import (
    ConfigurationError,
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderError,
    ProviderForbiddenError,
    ProviderTimeoutError,
)
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import (
    extract_first_asset_url,
    extract_outputs,
    normalize_wavespeed_response,
)
from backend.app.infrastructure.providers.wavespeed.legacy_http_client import (
    WaveSpeedLegacyHTTPClient,
)
from backend.app.infrastructure.providers.wavespeed.sdk_client import WaveSpeedSDKClient
from backend.app.scene_animation_generator import (
    SceneAnimationInput,
    SceneAnimationRequest,
    generate_scene_animations,
)
from backend.app.scene_generator import (
    PlannedScene,
    SceneSequenceRequest,
    _generate_scene_plan,
    generate_scene_sequence,
)
from backend.app.script_generator import ScriptRequest, generate_video_script
from backend.app.voiceover_generator import VoiceoverRequest, generate_voiceover


def _settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        wavespeed_api_key="test-key",
        **overrides,
    )


class FakeSDK:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = (
            {"outputs": ["https://example.test/output.png"]} if response is None else response
        )
        self.error = error
        self.run_calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        self.upload_calls: list[tuple[str, float]] = []

    def run(self, model: str, payload: dict[str, Any], **options: Any) -> Any:
        self.run_calls.append((model, payload, options))
        if self.error:
            raise self.error
        return self.response

    def upload(self, path: str, *, timeout: float) -> str:
        self.upload_calls.append((path, timeout))
        if self.error:
            raise self.error
        return "https://example.test/uploaded.bin"


def test_official_sdk_dependency_is_importable() -> None:
    assert tuple(int(part) for part in wavespeed.__version__.split(".")) >= (1, 0, 9)


def test_provider_mode_can_select_legacy_rollback_client() -> None:
    client = create_wavespeed_provider_client(_settings(wavespeed_provider_mode="legacy_http"))
    assert isinstance(client, WaveSpeedLegacyHTTPClient)


def test_provider_mode_selects_sdk_client_by_default() -> None:
    assert isinstance(create_wavespeed_provider_client(_settings()), WaveSpeedSDKClient)


def test_unsupported_provider_mode_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        create_wavespeed_provider_client(_settings(wavespeed_provider_mode="unknown"))


def test_legacy_rollback_client_uses_submit_and_poll(monkeypatch) -> None:
    submitted_payloads = []
    polled_urls = []

    class FakeHTTPClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(
        "backend.app.infrastructure.providers.wavespeed.legacy_http_client.httpx.Client",
        lambda **_kwargs: FakeHTTPClient(),
    )

    def fake_submit(_client, _key, model, payload, **_kwargs):
        submitted_payloads.append((model, payload))
        return {"urls": {"get": "https://example.test/status"}}

    def fake_poll(_client, _key, status_url, _timeout_message):
        polled_urls.append(status_url)
        return {"outputs": ["https://example.test/image.png"]}

    monkeypatch.setattr(
        "backend.app.infrastructure.providers.wavespeed.legacy_http_client.submit_prediction",
        fake_submit,
    )
    monkeypatch.setattr(
        "backend.app.infrastructure.providers.wavespeed.legacy_http_client.poll_prediction",
        fake_poll,
    )
    result = WaveSpeedLegacyHTTPClient(_settings()).run_model("model", {"prompt": "test"})

    assert result["outputs"] == ["https://example.test/image.png"]
    assert submitted_payloads == [("model", {"prompt": "test"})]
    assert polled_urls == ["https://example.test/status"]


def test_sdk_run_model_passes_supported_options_and_normalizes() -> None:
    sdk = FakeSDK(response={"outputs": ["https://example.test/image.png"]})
    client = WaveSpeedSDKClient(_settings(), sdk_client=sdk)

    result = client.run_model(
        "wavespeed-ai/model",
        {"prompt": "safe test"},
        timeout_seconds=12.5,
        poll_interval_seconds=0.25,
        enable_sync_mode=True,
    )

    assert result == {"outputs": ["https://example.test/image.png"]}
    assert sdk.run_calls == [
        (
            "wavespeed-ai/model",
            {"prompt": "safe test"},
            {"timeout": 12.5, "poll_interval": 0.25, "enable_sync_mode": True},
        )
    ]


def test_sdk_run_model_uses_settings_defaults() -> None:
    sdk = FakeSDK()
    settings = _settings(
        wavespeed_sdk_timeout_seconds=99,
        wavespeed_sdk_poll_interval_seconds=2,
        wavespeed_sdk_enable_sync_mode=True,
    )
    WaveSpeedSDKClient(settings, sdk_client=sdk).run_model("model", {})

    assert sdk.run_calls[0][2] == {
        "timeout": 99,
        "poll_interval": 2,
        "enable_sync_mode": True,
    }


def test_sdk_response_helpers_normalize_nested_data() -> None:
    response = normalize_wavespeed_response(
        {"data": {"status": "completed", "outputs": ["https://example.test/a.png"]}}
    )
    assert extract_outputs(response) == ["https://example.test/a.png"]
    assert extract_first_asset_url(response) == "https://example.test/a.png"


def test_sdk_upload_returns_url(tmp_path: Path) -> None:
    source = tmp_path / "asset.bin"
    source.write_bytes(b"asset")
    sdk = FakeSDK()
    client = WaveSpeedSDKClient(_settings(wavespeed_sdk_timeout_seconds=44), sdk_client=sdk)

    assert client.upload_file(source) == "https://example.test/uploaded.bin"
    assert sdk.upload_calls == [(str(source), 44)]


@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        (RuntimeError("HTTP 401 Unauthorized"), ProviderAuthError),
        (RuntimeError("HTTP 403 Forbidden"), ProviderForbiddenError),
        (TimeoutError("prediction timeout"), ProviderTimeoutError),
        (RuntimeError("other SDK failure"), ProviderError),
    ],
)
def test_sdk_errors_map_to_safe_provider_errors(
    error: Exception,
    expected_error: type[ProviderError],
) -> None:
    client = WaveSpeedSDKClient(_settings(), sdk_client=FakeSDK(error=error))
    with pytest.raises(expected_error) as raised:
        client.run_model("model", {})
    assert str(error) not in str(raised.value)


def test_sdk_malformed_response_maps_to_bad_response() -> None:
    client = WaveSpeedSDKClient(_settings(), sdk_client=FakeSDK(response={"unexpected": True}))
    with pytest.raises(ProviderBadResponseError):
        client.run_model("model", {})


def test_sdk_empty_outputs_map_to_bad_response() -> None:
    client = WaveSpeedSDKClient(_settings(), sdk_client=FakeSDK(response={"outputs": []}))
    with pytest.raises(ProviderBadResponseError):
        client.run_model("model", {})


class FakeProvider:
    def __init__(self, outputs: Any) -> None:
        self.outputs = outputs
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run_model(self, model: str, payload: dict[str, Any], **_options: Any) -> dict[str, Any]:
        self.calls.append((model, payload))
        return {"outputs": self.outputs}

    def upload_file(self, path: Path) -> str:
        return path.as_uri()


def test_art_style_uses_provider_client_boundary() -> None:
    provider = FakeProvider(["https://example.test/image.png"])
    result = generate_art_style_image(
        "unused",
        ArtStyleRequest(
            prompt="A cinematic mountain landscape",
            art_direction="Dramatic realism",
            enable_safety_checker=False,
        ),
        provider_client=provider,
    )
    assert result.image_url == "https://example.test/image.png"
    assert len(provider.calls) == 1


def test_sdk_backed_generator_selects_sdk_mode_by_default(monkeypatch) -> None:
    provider = FakeProvider(["https://example.test/image.png"])

    def fake_factory(settings, *, api_key=None):
        assert settings.wavespeed_provider_mode == "sdk"
        assert api_key == "test-key"
        return provider

    monkeypatch.setattr(
        "backend.app.art_style_generator.create_wavespeed_provider_client",
        fake_factory,
    )
    result = generate_art_style_image(
        "test-key",
        ArtStyleRequest(
            prompt="A cinematic mountain landscape",
            art_direction="Dramatic realism",
            enable_safety_checker=False,
        ),
        settings=_settings(),
    )

    assert result.image_url == "https://example.test/image.png"
    assert len(provider.calls) == 1


def test_voiceover_uses_provider_client_boundary() -> None:
    provider = FakeProvider(["https://example.test/voice.mp3"])
    result = generate_voiceover(
        "unused",
        VoiceoverRequest(text="Hello world"),
        provider_client=provider,
    )
    assert result.audio_url == "https://example.test/voice.mp3"
    assert len(provider.calls) == 1


def test_background_music_uses_provider_client_boundary() -> None:
    provider = FakeProvider(
        ["https://example.test/music-1.mp3", "https://example.test/music-2.mp3"]
    )
    result = generate_background_music(
        "unused",
        BackgroundMusicRequest(prompt="Dark cinematic instrumental music"),
        provider_client=provider,
    )
    assert result.audio_urls == [
        "https://example.test/music-1.mp3",
        "https://example.test/music-2.mp3",
    ]


def test_scene_animation_uses_provider_client_boundary() -> None:
    provider = FakeProvider(["https://example.test/scene.mp4"])
    result = generate_scene_animations(
        "unused",
        SceneAnimationRequest(
            scenes=[
                SceneAnimationInput(
                    scene_number=1,
                    image_url="https://example.test/image.png",
                    motion_prompt="Slow camera push forward",
                )
            ]
        ),
        provider_client=provider,
    )
    assert result.scenes[0].video_url == "https://example.test/scene.mp4"


class FakeLLMResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"title":"Title","event_name":"Event",'
                            '"script":"Legacy HTTP script",'
                            '"factual_basis":"Documented."}'
                        )
                    }
                }
            ]
        }


class FakeLLMClient:
    def __enter__(self) -> "FakeLLMClient":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def post(self, *_args: Any, **_kwargs: Any) -> FakeLLMResponse:
        return FakeLLMResponse()


def test_script_generation_remains_on_legacy_chat_completions(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.script_generator.httpx.Client",
        lambda **_kwargs: FakeLLMClient(),
    )
    result = generate_video_script("test-key", ScriptRequest())
    assert result.script == "Legacy HTTP script"


def test_scene_planner_remains_on_legacy_chat_completions(monkeypatch) -> None:
    content = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"scenes":['
                        '{"narration":"First",'
                        '"image_prompt":"A detailed cinematic first image prompt",'
                        '"motion_prompt":"A slow camera push"},'
                        '{"narration":"Second",'
                        '"image_prompt":"A detailed cinematic second image prompt",'
                        '"motion_prompt":"A gentle camera pan"}'
                        "]}"
                    )
                }
            }
        ]
    }

    class SceneResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return content

    class SceneClient(FakeLLMClient):
        def post(self, url, **_kwargs):
            assert url.endswith("/chat/completions")
            return SceneResponse()

    monkeypatch.setattr(
        "backend.app.scene_generator.httpx.Client",
        lambda **_kwargs: SceneClient(),
    )
    scenes = _generate_scene_plan(
        "test-key",
        SceneSequenceRequest(
            script="A sufficiently long script for scene planning.",
            art_direction="Dramatic cinematic realism",
        ),
    )
    assert len(scenes) == 2


def test_parallel_scene_rendering_uses_one_provider_client_per_scene(monkeypatch) -> None:
    planned = [
        PlannedScene(
            narration=f"Scene {index}",
            image_prompt=f"A sufficiently detailed cinematic image prompt number {index}",
            motion_prompt="A subtle camera movement",
        )
        for index in range(1, 4)
    ]
    clients = []
    used_client_ids = []

    class RenderClient:
        pass

    def factory():
        client = RenderClient()
        clients.append(client)
        return client

    def fake_render(_api_key, payload, *, provider_client, **_kwargs):
        used_client_ids.append(id(provider_client))
        return ArtStyleResponse(
            prompt=payload.prompt,
            style_name=payload.style_name,
            art_direction=payload.art_direction,
            styled_prompt=payload.prompt,
            model=payload.model,
            enable_safety_checker=payload.enable_safety_checker,
            safety_output=None,
            image_url="https://example.test/image.png",
            raw_output={},
        )

    monkeypatch.setattr("backend.app.scene_generator._generate_scene_plan", lambda *_args: planned)
    monkeypatch.setattr("backend.app.scene_generator.generate_art_style_image", fake_render)
    result = generate_scene_sequence(
        "test-key",
        SceneSequenceRequest(
            script="A sufficiently long script for safe parallel rendering.",
            art_direction="Dramatic cinematic realism",
        ),
        provider_client_factory=factory,
        settings=_settings(),
    )

    assert result.scene_count == 3
    assert len(clients) == 3
    assert len(set(used_client_ids)) == 3

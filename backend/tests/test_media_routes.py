from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.caption_style_generator import CaptionStyleResponse
from backend.app.core.config import Settings
from backend.app.core.errors import MediaProcessingError
from backend.app.main import create_app
from backend.app.video_generator import VideoGenerationRequest, generate_video


def test_caption_upload_route_persists_validated_safe_video(tmp_path, monkeypatch) -> None:
    root = tmp_path / "generated"
    settings = Settings(
        _env_file=None,
        app_env="test",
        generated_root=root,
        local_storage_root=root,
        database_url=f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}",
    )

    def fake_caption_render(payload, **_kwargs):
        assert Path(payload.input_video_path).is_file()
        assert payload.transcript_path == ""
        return CaptionStyleResponse(
            **payload.model_dump(),
            output_path=str(root / "captions" / "safe.mp4"),
            output_url="/generated/captions/safe.mp4",
            command=["pycaps", "render"],
            raw_output={"mocked": True},
        )

    monkeypatch.setattr(
        "backend.app.api.v1.captions.generate_caption_style_video",
        fake_caption_render,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/caption-style/generate",
            files={
                "input_video": (
                    "../../unsafe name.mp4",
                    b"\x00\x00\x00\x18ftypmp42video",
                    "video/mp4",
                )
            },
        )

    assert response.status_code == 200
    uploads = list((root / "uploads" / "captions" / "videos").glob("*.mp4"))
    assert len(uploads) == 1
    assert ".." not in uploads[0].name


def test_caption_upload_route_passes_uploaded_transcript_to_renderer(tmp_path, monkeypatch) -> None:
    root = tmp_path / "generated"
    settings = Settings(
        _env_file=None,
        app_env="test",
        generated_root=root,
        local_storage_root=root,
        database_url=f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}",
        transcription_provider="openai",
        openai_api_key="unused-because-upload-wins",
    )

    def fake_caption_render(payload, **_kwargs):
        assert Path(payload.input_video_path).is_file()
        assert Path(payload.transcript_path).read_text(encoding="utf-8").startswith("WEBVTT")
        assert payload.transcript_format == "vtt"
        return CaptionStyleResponse(
            **payload.model_dump(),
            output_path=str(root / "captions" / "safe.mp4"),
            output_url="/generated/captions/safe.mp4",
            command=["pycaps", "render", "--transcript", payload.transcript_path],
            raw_output={"mocked": True},
        )

    monkeypatch.setattr(
        "backend.app.api.v1.captions.generate_caption_style_video",
        fake_caption_render,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/caption-style/generate",
            data={"transcript_format": "vtt"},
            files={
                "input_video": (
                    "clip.mp4",
                    b"\x00\x00\x00\x18ftypmp42video",
                    "video/mp4",
                ),
                "transcript": (
                    "captions.vtt",
                    b"WEBVTT\n\n00:00.000 --> 00:01.000\nHello",
                    "text/vtt",
                ),
            },
        )

    assert response.status_code == 200
    assert response.json()["transcript_format"] == "vtt"


class FakeDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def download(self, url: str, destination: Path, expected_kind: str) -> Path:
        self.calls.append((url, expected_kind))
        suffix = {"image": ".png", "audio": ".mp3", "video": ".mp4"}[expected_kind]
        path = destination.with_suffix(suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mock")
        return path

    def close(self) -> None:
        raise AssertionError("Injected downloader must not be closed by generate_video")


def test_video_generator_uses_safe_downloader_boundary(tmp_path, monkeypatch) -> None:
    import backend.app.video_generator as video_module

    monkeypatch.setattr(video_module.shutil, "which", lambda _name: "ffmpeg")
    monkeypatch.setattr(
        video_module,
        "_render_scene_segment",
        lambda _source, output, *_args: output.write_bytes(b"segment"),
    )
    monkeypatch.setattr(
        video_module,
        "_concat_segments",
        lambda _segments, _list_path, output: output.write_bytes(b"visuals"),
    )
    monkeypatch.setattr(
        video_module,
        "_mix_audio",
        lambda _visuals, _voice, _music, output, *_args: output.write_bytes(b"video"),
    )
    caption_payloads = []

    def fake_caption_generator(payload, **_kwargs):
        caption_payloads.append(payload)
        return CaptionStyleResponse(
            **payload.model_dump(),
            output_path=str(tmp_path / "final.mp4"),
            output_url="/generated/captions/final.mp4",
            command=[],
            raw_output={"mocked": True, "filtered_trailing_cues": 2},
        )

    monkeypatch.setattr(video_module, "generate_caption_style_video", fake_caption_generator)
    downloader = FakeDownloader()
    response = generate_video(
        VideoGenerationRequest(
            image_urls=["https://example.com/image.png"],
            voiceover_url="https://example.com/voice.mp3",
            duration_seconds=5,
            reference_script="Reference narration text.",
            video_quality="low",
        ),
        downloader=downloader,  # type: ignore[arg-type]
        settings=Settings(
            _env_file=None,
            generated_root=tmp_path,
            local_storage_root=tmp_path,
        ),
    )

    assert response.captioned is True
    assert response.filtered_subtitle_cues == 2
    assert caption_payloads[0].reference_script == "Reference narration text."
    assert caption_payloads[0].video_quality == "low"
    assert response.video_quality == "low"
    assert [timing.step for timing in response.processing_timings] == [
        "download_assets",
        "render_scenes",
        "merge_scenes",
        "mix_audio",
        "total",
    ]
    assert downloader.calls == [
        ("https://example.com/image.png", "image"),
        ("https://example.com/voice.mp3", "audio"),
    ]


def test_ffmpeg_failure_does_not_expose_raw_stderr(monkeypatch) -> None:
    import subprocess

    import backend.app.video_generator as video_module

    def fail(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, ["ffmpeg"], stderr="sensitive internal detail")

    monkeypatch.setattr(video_module.subprocess, "run", fail)
    with pytest.raises(MediaProcessingError) as raised:
        video_module._run_command(["ffmpeg"], "testing")

    assert "sensitive internal detail" not in str(raised.value)

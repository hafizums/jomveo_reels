import subprocess
from pathlib import Path

import pytest

import backend.app.caption_style_generator as caption_module
from backend.app.caption_style_generator import CaptionStyleRequest
from backend.app.core.config import Settings
from backend.app.core.errors import MediaProcessingError
from backend.app.infrastructure.providers.transcription import TranscriptionResult
from backend.app.infrastructure.providers.transcription.factory import (
    create_transcription_provider,
)


class FakeTranscriptionProvider:
    def __init__(
        self, transcript_format: str = "srt", transcript_text: str = "generated transcript"
    ) -> None:
        self.transcript_format = transcript_format
        self.transcript_text = transcript_text
        self.calls: list[dict] = []
        self.generated_path: Path | None = None

    def transcribe_to_file(self, input_media_path, output_directory, **kwargs):
        self.calls.append(
            {
                "input_media_path": input_media_path,
                "output_directory": output_directory,
                **kwargs,
            }
        )
        output_directory.mkdir(parents=True, exist_ok=True)
        self.generated_path = output_directory / f"generated.{self.transcript_format}"
        self.generated_path.write_text(self.transcript_text, encoding="utf-8")
        return TranscriptionResult(
            transcript_path=self.generated_path,
            transcript_format=self.transcript_format,
            provider="openai",
            model="whisper-1",
        )


def _settings(tmp_path: Path, **values) -> Settings:
    return Settings(
        _env_file=None,
        generated_root=tmp_path,
        local_storage_root=tmp_path,
        **values,
    )


def _request(media: Path, **values) -> CaptionStyleRequest:
    return CaptionStyleRequest(input_video_path=str(media), **values)


def _successful_pycaps(command, **_kwargs):
    output = Path(command[command.index("--output") + 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"captioned video")
    return subprocess.CompletedProcess(command, 0)


def test_uploaded_transcript_wins_and_skips_provider(tmp_path, monkeypatch) -> None:
    media = tmp_path / "clip.mp4"
    transcript = tmp_path / "uploaded.vtt"
    media.write_bytes(b"video")
    transcript.write_text("WEBVTT", encoding="utf-8")
    monkeypatch.setattr(
        caption_module,
        "create_transcription_provider",
        lambda _settings: pytest.fail("provider must not be created"),
    )
    monkeypatch.setattr(caption_module.subprocess, "run", _successful_pycaps)

    response = caption_module.generate_caption_style_video(
        _request(media, transcript_path=str(transcript), transcript_format="vtt"),
        settings=_settings(tmp_path),
    )

    assert response.transcript_path == str(transcript)
    assert response.transcript_format == "vtt"
    assert response.command[response.command.index("--transcript") + 1] == str(transcript)
    assert response.command[response.command.index("--video-quality") + 1] == "middle"


def test_provider_none_preserves_pycaps_without_transcript(tmp_path, monkeypatch) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    monkeypatch.setattr(caption_module.subprocess, "run", _successful_pycaps)

    response = caption_module.generate_caption_style_video(
        _request(media),
        settings=_settings(tmp_path, transcription_provider="none"),
    )

    assert response.transcript_path == ""
    assert "--transcript" not in response.command


def test_openai_transcript_is_passed_to_pycaps(tmp_path, monkeypatch) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    provider = FakeTranscriptionProvider("vtt")
    monkeypatch.setattr(caption_module, "create_transcription_provider", lambda _settings: provider)
    monkeypatch.setattr(caption_module.subprocess, "run", _successful_pycaps)

    response = caption_module.generate_caption_style_video(
        _request(media, language_hint="ms"),
        settings=_settings(
            tmp_path,
            transcription_provider="openai",
            openai_api_key="test-key",
            transcription_output_format="vtt",
            transcription_prompt="Preferred spelling: JomVeo",
        ),
    )

    assert provider.calls[0]["language_hint"] == "ms"
    assert provider.calls[0]["prompt"] == "Preferred spelling: JomVeo"
    assert provider.calls[0]["output_format"] == "vtt"
    assert response.transcript_path == str(provider.generated_path)
    assert response.transcript_format == "vtt"
    assert response.command[response.command.index("--transcript") + 1] == str(
        provider.generated_path
    )
    assert provider.generated_path is not None and provider.generated_path.exists()
    assert [timing.step for timing in response.processing_timings] == [
        "transcription",
        "caption_render",
        "caption_total",
    ]


def test_reference_script_removes_unmatched_trailing_whisper_cue(tmp_path, monkeypatch) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    provider = FakeTranscriptionProvider(
        transcript_text=(
            "1\n00:00:00,000 --> 00:00:02,000\nMahkota itu akhirnya jatuh dalam diam.\n\n"
            "2\n00:00:57,000 --> 00:00:59,000\nSari kata pelajar Mediacorp Pte Ltd\n"
        )
    )
    monkeypatch.setattr(caption_module, "create_transcription_provider", lambda _settings: provider)
    monkeypatch.setattr(caption_module.subprocess, "run", _successful_pycaps)

    response = caption_module.generate_caption_style_video(
        _request(
            media,
            reference_script="Mahkota itu akhirnya jatuh dalam diam.",
        ),
        settings=_settings(
            tmp_path,
            transcription_provider="openai",
            openai_api_key="test-key",
        ),
    )

    transcript = Path(response.transcript_path).read_text(encoding="utf-8")
    assert "Mahkota" in transcript
    assert "Mediacorp" not in transcript
    assert response.raw_output["filtered_trailing_cues"] == 1


def test_openai_without_api_key_raises_friendly_error(tmp_path) -> None:
    settings = _settings(tmp_path, transcription_provider="openai", openai_api_key="")

    with pytest.raises(MediaProcessingError, match="OPENAI_API_KEY is not configured"):
        create_transcription_provider(settings)


def test_generated_transcript_is_removed_when_pycaps_fails(tmp_path, monkeypatch) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    provider = FakeTranscriptionProvider()
    monkeypatch.setattr(caption_module, "create_transcription_provider", lambda _settings: provider)

    def fail(command, **_kwargs):
        raise subprocess.CalledProcessError(1, command, stderr="render failed")

    monkeypatch.setattr(caption_module.subprocess, "run", fail)

    with pytest.raises(MediaProcessingError, match="Caption rendering failed"):
        caption_module.generate_caption_style_video(
            _request(media),
            settings=_settings(
                tmp_path,
                transcription_provider="openai",
                openai_api_key="test-key",
            ),
        )

    assert provider.generated_path is not None
    assert not provider.generated_path.exists()

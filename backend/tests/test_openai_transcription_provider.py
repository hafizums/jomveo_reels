from types import SimpleNamespace

from backend.app.infrastructure.providers.transcription.openai_provider import (
    OpenAITranscriptionProvider,
)


class FakeTranscriptions:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["file"].read() == b"media"
        return self.response


def _provider(response):
    transcriptions = FakeTranscriptions(response)
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))
    provider = OpenAITranscriptionProvider(
        api_key="secret-test-key",
        model="whisper-1",
        timeout_seconds=30,
        client=client,
    )
    return provider, transcriptions


def test_openai_provider_sends_supported_options_and_writes_srt(tmp_path) -> None:
    media = tmp_path / "unsafe media name.mp4"
    media.write_bytes(b"media")
    provider, transcriptions = _provider("1\n00:00:00,000 --> 00:00:01,000\nHello\n")

    result = provider.transcribe_to_file(
        media,
        tmp_path / "transcripts",
        language_hint="ms",
        prompt="Names: JomVeo",
        output_format="srt",
    )

    call = transcriptions.calls[0]
    assert call["model"] == "whisper-1"
    assert call["response_format"] == "srt"
    assert call["language"] == "ms"
    assert call["prompt"] == "Names: JomVeo"
    assert result.transcript_path.suffix == ".srt"
    assert result.transcript_path.read_text(encoding="utf-8").endswith("Hello\n")
    assert result.transcript_format == "srt"
    assert result.provider == "openai"


def test_openai_provider_normalizes_object_text_and_writes_vtt(tmp_path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    provider, transcriptions = _provider(
        SimpleNamespace(text="WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n")
    )

    result = provider.transcribe_to_file(
        media,
        tmp_path / "transcripts",
        output_format="vtt",
    )

    call = transcriptions.calls[0]
    assert "language" not in call
    assert "prompt" not in call
    assert result.transcript_path.suffix == ".vtt"
    assert result.transcript_path.read_text(encoding="utf-8").startswith("WEBVTT")


def test_openai_provider_does_not_log_key_or_transcript(tmp_path, caplog) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    secret_transcript = "private transcript content"
    provider, _transcriptions = _provider(secret_transcript)

    provider.transcribe_to_file(media, tmp_path / "transcripts")

    assert "secret-test-key" not in caplog.text
    assert secret_transcript not in caplog.text

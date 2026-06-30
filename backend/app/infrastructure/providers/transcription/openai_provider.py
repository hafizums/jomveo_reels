import uuid
from pathlib import Path
from typing import Any

from openai import APITimeoutError, OpenAI, OpenAIError

from backend.app.core.errors import MediaProcessingError, ValidationAppError
from backend.app.storage.paths import sanitize_filename

from .base import TranscriptionResult


class OpenAITranscriptionProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int,
        *,
        client: Any | None = None,
    ) -> None:
        self.client = client or OpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model

    def transcribe_to_file(
        self,
        input_media_path: Path,
        output_directory: Path,
        *,
        language_hint: str = "",
        prompt: str = "",
        output_format: str = "srt",
    ) -> TranscriptionResult:
        normalized_format = output_format.strip().casefold()
        if normalized_format not in {"srt", "vtt"}:
            raise ValidationAppError("OpenAI transcription output format must be srt or vtt.")
        if not input_media_path.is_file():
            raise ValidationAppError("Transcription input media was not found.")

        request: dict[str, Any] = {
            "model": self.model,
            "response_format": normalized_format,
        }
        if language_hint.strip():
            request["language"] = language_hint.strip()
        if prompt.strip():
            request["prompt"] = prompt.strip()

        try:
            with input_media_path.open("rb") as media_file:
                transcription = self.client.audio.transcriptions.create(
                    file=media_file,
                    **request,
                )
        except APITimeoutError as exc:
            raise MediaProcessingError("OpenAI transcription timed out.") from exc
        except (OpenAIError, TimeoutError) as exc:
            raise MediaProcessingError("OpenAI transcription failed.") from exc

        transcript_text = self._normalize_transcript_text(transcription)
        if not transcript_text.strip():
            raise MediaProcessingError("OpenAI transcription returned an empty transcript.")

        output_directory.mkdir(parents=True, exist_ok=True)
        safe_name = Path(sanitize_filename(input_media_path.stem, "media")).stem
        output_path = output_directory / (
            f"{safe_name}-openai-{uuid.uuid4().hex[:8]}.{normalized_format}"
        )
        try:
            output_path.write_text(transcript_text, encoding="utf-8")
        except OSError as exc:
            raise MediaProcessingError("OpenAI transcript could not be saved.") from exc

        return TranscriptionResult(
            transcript_path=output_path,
            transcript_format=normalized_format,
            provider="openai",
            model=self.model,
        )

    @staticmethod
    def _normalize_transcript_text(transcription: Any) -> str:
        if isinstance(transcription, str):
            return transcription
        text = getattr(transcription, "text", None)
        if isinstance(text, str):
            return text
        if isinstance(transcription, bytes):
            return transcription.decode("utf-8")
        return str(transcription)

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError, MediaProcessingError

from .base import TranscriptionProvider
from .openai_provider import OpenAITranscriptionProvider


def create_transcription_provider(settings: Settings) -> TranscriptionProvider | None:
    provider = settings.transcription_provider.strip().casefold()
    if provider == "none":
        return None
    if provider == "openai":
        if not settings.openai_api_key.strip():
            raise MediaProcessingError(
                "OpenAI transcription is enabled but OPENAI_API_KEY is not configured."
            )
        return OpenAITranscriptionProvider(
            api_key=settings.openai_api_key,
            model=settings.transcription_model,
            timeout_seconds=settings.transcription_timeout_seconds,
        )
    raise ConfigurationError(f"Unsupported TRANSCRIPTION_PROVIDER: {provider}")

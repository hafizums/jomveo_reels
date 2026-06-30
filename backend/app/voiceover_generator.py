from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.core.config import Settings, get_settings
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import (
    WaveSpeedProviderClient,
    extract_first_asset_url,
)

GEMINI_FLASH_TTS_MODEL = "google/gemini-2.5-flash/text-to-speech"
DEFAULT_VOICEOVER_MODEL = GEMINI_FLASH_TTS_MODEL
DEFAULT_VOICE_ID = "Achernar"
DEFAULT_VOICE_LANGUAGE = "English (United States)"
DEFAULT_SIMILARITY = 0.85
DEFAULT_STABILITY = 0.45
DEFAULT_USE_SPEAKER_BOOST = True
GEMINI_VOICES = {
    "Achernar",
    "Achird",
    "Algenib",
    "Algieba",
    "Alnilam",
    "Aoede",
    "Autonoe",
    "Callirrhoe",
    "Charon",
    "Despina",
    "Enceladus",
    "Erinome",
    "Fenrir",
    "Gacrux",
    "Iapetus",
    "Kore",
    "Laomedeia",
    "Leda",
    "Orus",
    "Puck",
    "Pulcherrima",
    "Rasalgethi",
    "Sadachbia",
    "Sadaltager",
    "Schedar",
    "Sulafat",
    "Umbriel",
    "Vindemiatrix",
    "Zephyr",
    "Zubenelgenubi",
}


class VoiceoverRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: str = Field(default=DEFAULT_VOICE_ID, max_length=100)
    similarity: float = Field(default=DEFAULT_SIMILARITY, ge=0.0, le=1.0)
    stability: float = Field(default=DEFAULT_STABILITY, ge=0.0, le=1.0)
    use_speaker_boost: bool = Field(default=DEFAULT_USE_SPEAKER_BOOST)
    style_name: str = Field(default="Calm Narrator", max_length=80)
    model: str = Field(default=DEFAULT_VOICEOVER_MODEL, min_length=1, max_length=120)
    language: str = Field(default=DEFAULT_VOICE_LANGUAGE, min_length=2, max_length=40)
    gender: str = Field(default="Female", min_length=2, max_length=20)
    speaker_name: str = Field(default="Narrator", min_length=1, max_length=80)


class VoiceoverResponse(BaseModel):
    text: str
    voice_id: str
    similarity: float
    stability: float
    use_speaker_boost: bool
    style_name: str
    model: str
    language: str
    gender: str
    speaker_name: str
    audio_url: str
    raw_output: dict[str, Any]


def generate_voiceover(
    api_key: str,
    payload: VoiceoverRequest,
    *,
    provider_client: WaveSpeedProviderClient | None = None,
    settings: Settings | None = None,
) -> VoiceoverResponse:
    settings = settings or get_settings()
    provider_client = provider_client or create_wavespeed_provider_client(settings, api_key=api_key)
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Voiceover text cannot be empty.")

    if payload.model == GEMINI_FLASH_TTS_MODEL:
        if payload.voice_id not in GEMINI_VOICES:
            raise HTTPException(status_code=400, detail="Select a valid Gemini TTS voice.")
        spoken_text = payload.text.strip()
        speaker_prefix = f"{payload.speaker_name}:"
        if not spoken_text.casefold().startswith(speaker_prefix.casefold()):
            spoken_text = f"{speaker_prefix} {spoken_text}"
        if len(spoken_text.encode("utf-8")) > 8000:
            raise HTTPException(
                status_code=400, detail="Gemini TTS text must not exceed 8,000 bytes."
            )
        provider_payload: dict[str, Any] = {
            "text": spoken_text,
            "language": payload.language,
            "speakers": [
                {
                    "speaker": payload.speaker_name,
                    "voice": payload.voice_id,
                }
            ],
        }
    else:
        provider_payload = {
            "text": payload.text,
            "voice_id": payload.voice_id,
            "similarity": payload.similarity,
            "stability": payload.stability,
            "use_speaker_boost": payload.use_speaker_boost,
        }

    output = provider_client.run_model(payload.model, provider_payload)

    audio_url = extract_first_asset_url(output)

    return VoiceoverResponse(
        text=payload.text,
        voice_id=payload.voice_id,
        similarity=payload.similarity,
        stability=payload.stability,
        use_speaker_boost=payload.use_speaker_boost,
        style_name=payload.style_name,
        model=payload.model,
        language=payload.language,
        gender=payload.gender,
        speaker_name=payload.speaker_name,
        audio_url=audio_url,
        raw_output=output,
    )

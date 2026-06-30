from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from backend.app.core.config import Settings


@dataclass(frozen=True)
class AssetCreate:
    url: str
    asset_type: str
    source_field: str
    scene_number: int | None = None


def calculate_provider_expires_at(created_at: datetime, settings: Settings) -> datetime:
    return created_at + timedelta(days=settings.provider_asset_retention_days)


def _type(field: str, url: str) -> str:
    value = f"{field} {url}".casefold()
    if "image" in value or url.casefold().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if "audio" in value or url.casefold().endswith((".mp3", ".wav", ".m4a")):
        return "audio"
    if "video" in value or url.casefold().endswith((".mp4", ".webm", ".mov")):
        return "video"
    if "caption" in value or url.casefold().endswith((".srt", ".vtt")):
        return "caption"
    return "other"


def extract_asset_candidates(result: dict[str, Any]) -> list[AssetCreate]:
    found: dict[str, AssetCreate] = {}
    allowed = {
        "image_url",
        "audio_url",
        "audio_urls",
        "video_url",
        "output_url",
        "captions_url",
        "outputs",
    }

    def walk(value: Any, field: str = "", scene_number: int | None = None) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "raw_output" and isinstance(child, dict):
                    walk(child.get("outputs"), "outputs", scene_number)
                elif key == "scenes" and isinstance(child, list):
                    for index, scene in enumerate(child, 1):
                        walk(scene, "scenes", index)
                elif key in allowed:
                    walk(child, key, scene_number)
        elif isinstance(value, list):
            for child in value:
                walk(child, field, scene_number)
        elif isinstance(value, str) and (
            value.startswith(("http://", "https://")) or value.startswith("/generated/")
        ):
            found.setdefault(value, AssetCreate(value, _type(field, value), field, scene_number))

    walk(result)
    return list(found.values())

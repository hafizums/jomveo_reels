import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.app.core.errors import MediaProcessingError

logger = logging.getLogger(__name__)


class MediaProbeResult(BaseModel):
    duration_seconds: float | None
    format_name: str | None
    width: int | None
    height: int | None
    has_audio: bool
    has_video: bool


def probe_media(path: Path) -> MediaProbeResult:
    if not path.is_file():
        raise MediaProcessingError("Media file is unavailable for probing.")
    if not shutil.which("ffprobe"):
        raise MediaProcessingError("FFprobe is not installed or available on PATH.")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,format_name:stream=codec_type,width,height",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload: dict[str, Any] = json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        logger.exception("ffprobe_failed")
        raise MediaProcessingError("Could not inspect the media file.") from exc

    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    format_data = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = format_data.get("duration")
    return MediaProbeResult(
        duration_seconds=float(duration) if duration is not None else None,
        format_name=format_data.get("format_name"),
        width=video_stream.get("width") if video_stream else None,
        height=video_stream.get("height") if video_stream else None,
        has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
        has_video=video_stream is not None,
    )

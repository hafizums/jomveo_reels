import logging
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from fastapi import UploadFile
from pydantic import BaseModel, Field

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import MediaProcessingError, UploadValidationError, ValidationAppError
from backend.app.infrastructure.providers.transcription import create_transcription_provider
from backend.app.media.timing import ProcessingTiming, processing_timing
from backend.app.media.transcript_filter import filter_trailing_hallucinated_cues
from backend.app.media.validation import validate_upload_file
from backend.app.storage.base import StorageBackend
from backend.app.storage.local import LocalStorageBackend
from backend.app.storage.paths import make_object_key, sanitize_filename

DEFAULT_CAPTION_TEMPLATE = "minimalist"
DEFAULT_TRANSCRIPT_FORMAT = "auto"
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "generated" / "captions"
UPLOAD_DIRECTORY = Path(__file__).resolve().parents[1] / "generated" / "uploads" / "captions"
logger = logging.getLogger(__name__)
VideoQuality = Literal["low", "middle", "high", "very_high"]


class CaptionStyleRequest(BaseModel):
    input_video_path: str = Field(..., min_length=1, max_length=500)
    template_name: str = Field(default=DEFAULT_CAPTION_TEMPLATE, min_length=1, max_length=100)
    transcript_path: str = Field(default="", max_length=500)
    transcript_format: str = Field(default=DEFAULT_TRANSCRIPT_FORMAT, min_length=3, max_length=40)
    language_hint: str = Field(default="", max_length=20)
    style_name: str = Field(default="Minimalist", max_length=80)
    output_basename: str = Field(default="", max_length=120)
    reference_script: str = Field(default="", max_length=10000)
    video_quality: VideoQuality = "middle"


class CaptionStyleResponse(BaseModel):
    input_video_path: str
    template_name: str
    transcript_path: str
    transcript_format: str
    language_hint: str
    style_name: str
    output_path: str
    output_url: str
    command: list[str]
    raw_output: dict[str, Any]
    processing_timings: list[ProcessingTiming] = Field(default_factory=list)
    video_quality: VideoQuality = "middle"


def _sanitize_basename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_")
    return slug or "captioned-video"


def _resolve_output_path(request: CaptionStyleRequest, settings: Settings) -> Path:
    output_directory = settings.local_storage_root / "captions"
    output_directory.mkdir(parents=True, exist_ok=True)
    basename = request.output_basename or request.style_name or request.template_name
    return output_directory / f"{_sanitize_basename(basename)}.mp4"


def _resolve_pycaps_command() -> list[str]:
    exe_name = "pycaps.exe" if os.name == "nt" else "pycaps"
    local_exe = Path(sys.executable).resolve().with_name(exe_name)
    if local_exe.exists():
        return [str(local_exe)]
    return ["pycaps"]


def _build_command(request: CaptionStyleRequest, output_path: Path) -> list[str]:
    command = _resolve_pycaps_command() + [
        "render",
        "--input",
        request.input_video_path,
        "--output",
        str(output_path),
        "--template",
        request.template_name,
        "--video-quality",
        request.video_quality,
    ]

    if request.transcript_path.strip():
        command.extend(["--transcript", request.transcript_path.strip()])
        command.extend(["--transcript-format", request.transcript_format])

    if request.language_hint.strip():
        command.extend(["--lang", request.language_hint.strip()])

    return command


def save_uploaded_file(
    upload: UploadFile,
    category: str,
    *,
    storage: StorageBackend | None = None,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    storage = storage or LocalStorageBackend(
        settings.local_storage_root,
        settings.public_generated_url_prefix,
    )
    try:
        kind = {"videos": "video", "transcripts": "transcript"}[category]
    except KeyError as exc:
        raise ValidationAppError("Unsupported upload category.") from exc
    validated = validate_upload_file(upload, kind, settings.max_upload_bytes)
    filename = f"{uuid.uuid4().hex[:8]}-{sanitize_filename(validated.filename)}"
    key = make_object_key(f"uploads/captions/{category}", filename)

    temporary_path: Path | None = None
    try:
        settings.local_storage_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=settings.local_storage_root,
            prefix="caption-upload-",
            suffix=".part",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            copied = 0
            upload.file.seek(0)
            while chunk := upload.file.read(1024 * 1024):
                copied += len(chunk)
                if copied > settings.max_upload_bytes:
                    raise UploadValidationError("Uploaded file exceeds the configured size limit.")
                temporary.write(chunk)
        stored = storage.save_file(key, temporary_path, validated.content_type)
        return storage.open_path(stored.key)
    finally:
        upload.file.seek(0)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def generate_caption_style_video(
    request: CaptionStyleRequest,
    *,
    settings: Settings | None = None,
) -> CaptionStyleResponse:
    settings = settings or get_settings()
    input_path = Path(request.input_video_path)
    if not input_path.exists():
        raise ValidationAppError("Input video was not found.")

    if request.transcript_path.strip() and not Path(request.transcript_path).exists():
        raise ValidationAppError("Transcript was not found.")

    working_request = request
    generated_transcript_path: Path | None = None
    succeeded = False
    total_started = perf_counter()
    timings: list[ProcessingTiming] = []
    filtered_trailing_cues = 0

    try:
        if not request.transcript_path.strip():
            provider = create_transcription_provider(settings)
            if provider is not None:
                transcription_started = perf_counter()
                result = provider.transcribe_to_file(
                    input_media_path=input_path,
                    output_directory=settings.local_storage_root / "captions" / "transcripts",
                    language_hint=request.language_hint,
                    prompt=settings.transcription_prompt,
                    output_format=settings.transcription_output_format,
                )
                generated_transcript_path = result.transcript_path
                if not generated_transcript_path.is_file():
                    raise MediaProcessingError("Transcription did not produce a transcript file.")
                filtered_trailing_cues = filter_trailing_hallucinated_cues(
                    generated_transcript_path,
                    result.transcript_format,
                    request.reference_script,
                )
                timings.append(
                    processing_timing(
                        "transcription",
                        "Transcribe audio",
                        perf_counter() - transcription_started,
                    )
                )
                working_request = request.model_copy(
                    update={
                        "transcript_path": str(generated_transcript_path),
                        "transcript_format": result.transcript_format,
                    }
                )

        output_path = _resolve_output_path(working_request, settings)
        command = _build_command(working_request, output_path)

        caption_render_started = perf_counter()
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=1800,
            )
        except FileNotFoundError as exc:
            raise MediaProcessingError(
                "Caption rendering is unavailable because pycaps is not installed."
            ) from exc
        except subprocess.CalledProcessError as exc:
            logger.error("caption_render_failed: %s", (exc.stderr or "")[-3000:])
            raise MediaProcessingError("Caption rendering failed.") from exc
        except subprocess.TimeoutExpired as exc:
            raise MediaProcessingError("Caption rendering timed out.") from exc

        if not output_path.exists():
            raise MediaProcessingError("Caption rendering did not produce an output file.")
        timings.append(
            processing_timing(
                "caption_render",
                "Burn captions",
                perf_counter() - caption_render_started,
            )
        )
        timings.append(
            processing_timing(
                "caption_total",
                "Caption processing total",
                perf_counter() - total_started,
            )
        )

        url_prefix = settings.public_generated_url_prefix.rstrip("/")
        output_url = f"{url_prefix}/captions/{output_path.name}"
        response = CaptionStyleResponse(
            input_video_path=working_request.input_video_path,
            template_name=working_request.template_name,
            transcript_path=working_request.transcript_path,
            transcript_format=working_request.transcript_format,
            language_hint=working_request.language_hint,
            style_name=working_request.style_name,
            output_path=str(output_path),
            output_url=output_url,
            command=command,
            raw_output={
                "rendered": True,
                "filtered_trailing_cues": filtered_trailing_cues,
            },
            processing_timings=timings,
            video_quality=working_request.video_quality,
        )
        succeeded = True
        return response
    finally:
        if generated_transcript_path is not None and not succeeded:
            generated_transcript_path.unlink(missing_ok=True)

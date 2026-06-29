import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field

DEFAULT_CAPTION_TEMPLATE = "minimalist"
DEFAULT_TRANSCRIPT_FORMAT = "auto"
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "generated" / "captions"
UPLOAD_DIRECTORY = Path(__file__).resolve().parents[1] / "generated" / "uploads" / "captions"


class CaptionStyleRequest(BaseModel):
    input_video_path: str = Field(..., min_length=1, max_length=500)
    template_name: str = Field(default=DEFAULT_CAPTION_TEMPLATE, min_length=1, max_length=100)
    transcript_path: str = Field(default="", max_length=500)
    transcript_format: str = Field(default=DEFAULT_TRANSCRIPT_FORMAT, min_length=3, max_length=40)
    language_hint: str = Field(default="", max_length=20)
    style_name: str = Field(default="Minimalist", max_length=80)
    output_basename: str = Field(default="", max_length=120)


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


def _sanitize_basename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_")
    return slug or "captioned-video"


def _sanitize_filename(value: str) -> str:
    filename = Path(value).name
    stem = _sanitize_basename(Path(filename).stem)
    suffix = Path(filename).suffix.lower()
    return f"{stem}{suffix}"


def _resolve_output_path(request: CaptionStyleRequest) -> Path:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    basename = request.output_basename or request.style_name or request.template_name
    return OUTPUT_DIRECTORY / f"{_sanitize_basename(basename)}.mp4"


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
    ]

    if request.transcript_path.strip():
        command.extend(["--transcript", request.transcript_path.strip()])
        command.extend(["--transcript-format", request.transcript_format])

    if request.language_hint.strip():
        command.extend(["--lang", request.language_hint.strip()])

    return command


def save_uploaded_file(upload: UploadFile, category: str) -> Path:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")

    destination_directory = UPLOAD_DIRECTORY / category
    destination_directory.mkdir(parents=True, exist_ok=True)

    sanitized_name = _sanitize_filename(upload.filename)
    destination = destination_directory / f"{uuid.uuid4().hex[:8]}-{sanitized_name}"

    upload.file.seek(0)
    with destination.open("wb") as output_file:
        shutil.copyfileobj(upload.file, output_file)
    return destination


def generate_caption_style_video(request: CaptionStyleRequest) -> CaptionStyleResponse:
    input_path = Path(request.input_video_path)
    if not input_path.exists():
        raise HTTPException(
            status_code=400, detail=f"Input video not found: {request.input_video_path}"
        )

    if request.transcript_path.strip() and not Path(request.transcript_path).exists():
        raise HTTPException(
            status_code=400, detail=f"Transcript not found: {request.transcript_path}"
        )

    output_path = _resolve_output_path(request)
    command = _build_command(request, output_path)

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "pycaps is not installed or not available on PATH. Install it from the GitHub repo "
                "and run `playwright install chromium` before using the caption module."
            ),
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or "pycaps render failed."
        raise HTTPException(status_code=502, detail=detail) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="Timed out waiting for pycaps to finish rendering the captioned video.",
        ) from exc

    if not output_path.exists():
        raise HTTPException(
            status_code=502,
            detail="pycaps finished without producing the expected output video file.",
        )

    output_url = f"/generated/captions/{output_path.name}"
    return CaptionStyleResponse(
        input_video_path=request.input_video_path,
        template_name=request.template_name,
        transcript_path=request.transcript_path,
        transcript_format=request.transcript_format,
        language_hint=request.language_hint,
        style_name=request.style_name,
        output_path=str(output_path),
        output_url=output_url,
        command=command,
        raw_output={
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )

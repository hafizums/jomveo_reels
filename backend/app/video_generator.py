import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.caption_style_generator import (
    CaptionStyleRequest,
    generate_caption_style_video,
)


VIDEO_OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "generated" / "videos"
MAX_ASSET_BYTES = 100 * 1024 * 1024
FPS = 30

AspectRatio = Literal["9:16", "16:9", "1:1", "4:5"]
VisualSource = Literal["stills", "animated"]

ASPECT_DIMENSIONS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}


class VideoGenerationRequest(BaseModel):
    title: str = Field(default="Generated video", max_length=200)
    duration_seconds: int = Field(default=60, ge=5, le=180)
    aspect_ratio: AspectRatio = "9:16"
    visual_source: VisualSource = "stills"
    image_urls: list[str] = Field(default_factory=list, max_length=10)
    video_urls: list[str] = Field(default_factory=list, max_length=10)
    voiceover_url: str = Field(..., min_length=8, max_length=2000)
    music_url: str = Field(default="", max_length=2000)
    music_volume: float = Field(default=0.16, ge=0.0, le=1.0)
    caption_template: str = Field(default="minimalist", min_length=1, max_length=100)
    caption_style_name: str = Field(default="Minimalist", max_length=80)
    language_hint: str = Field(default="", max_length=20)


class VideoGenerationResponse(BaseModel):
    job_id: str
    title: str
    duration_seconds: int
    aspect_ratio: AspectRatio
    visual_source: VisualSource
    width: int
    height: int
    scene_count: int
    captioned: bool
    output_path: str
    output_url: str


def _run_command(command: list[str], operation: str, timeout: int = 1800) -> None:
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed or is not available on PATH.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"Timed out while {operation}.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or f"FFmpeg failed while {operation}.").strip()
        raise HTTPException(status_code=502, detail=detail[-3000:]) from exc


def _validate_remote_url(url: str, asset_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail=f"{asset_name} must be a valid HTTP or HTTPS URL.",
        )


def _download_asset(client: httpx.Client, url: str, destination: Path, asset_name: str) -> None:
    _validate_remote_url(url, asset_name)
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_ASSET_BYTES:
                raise HTTPException(status_code=413, detail=f"{asset_name} exceeds the 100 MB limit.")

            downloaded = 0
            with destination.open("wb") as output:
                for chunk in response.iter_bytes():
                    downloaded += len(chunk)
                    if downloaded > MAX_ASSET_BYTES:
                        raise HTTPException(status_code=413, detail=f"{asset_name} exceeds the 100 MB limit.")
                    output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except (httpx.HTTPError, ValueError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=f"Could not download {asset_name}: {exc}") from exc


def _render_scene_segment(
    image_path: Path,
    output_path: Path,
    width: int,
    height: int,
    frame_count: int,
) -> None:
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "zoompan="
        "z='min(zoom+0.0008,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frame_count}:s={width}x{height}:fps={FPS},"
        "format=yuv420p"
    )
    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-i",
        str(image_path),
        "-vf",
        video_filter,
        "-frames:v",
        str(frame_count),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    _run_command(command, "rendering a scene")


def _render_animated_scene_segment(
    video_path: Path,
    output_path: Path,
    width: int,
    height: int,
    frame_count: int,
) -> None:
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={FPS},setsar=1,format=yuv420p"
    )
    command = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(video_path),
        "-vf",
        video_filter,
        "-frames:v",
        str(frame_count),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    _run_command(command, "rendering an animated scene")


def _concat_segments(segment_paths: list[Path], list_path: Path, output_path: Path) -> None:
    entries = [f"file '{path.resolve().as_posix().replace(chr(39), chr(39) * 2)}'" for path in segment_paths]
    list_path.write_text("\n".join(entries), encoding="utf-8")
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(output_path),
    ]
    _run_command(command, "joining scene segments")


def _mix_audio(
    visuals_path: Path,
    voiceover_path: Path,
    music_path: Path | None,
    output_path: Path,
    duration_seconds: int,
    music_volume: float,
) -> None:
    command = ["ffmpeg", "-y", "-i", str(visuals_path), "-i", str(voiceover_path)]

    if music_path:
        command.extend(["-stream_loop", "-1", "-i", str(music_path)])
        audio_filter = (
            f"[1:a]volume=1,apad,atrim=0:{duration_seconds}[voice];"
            f"[2:a]volume={music_volume},apad,atrim=0:{duration_seconds}[music];"
            "[voice][music]amix=inputs=2:duration=longest:dropout_transition=2,"
            f"atrim=0:{duration_seconds}[audio]"
        )
    else:
        audio_filter = f"[1:a]apad,atrim=0:{duration_seconds}[audio]"

    command.extend(
        [
            "-filter_complex",
            audio_filter,
            "-map",
            "0:v:0",
            "-map",
            "[audio]",
            "-t",
            str(duration_seconds),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_command(command, "mixing narration and background music")


def generate_video(payload: VideoGenerationRequest) -> VideoGenerationResponse:
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=500, detail="FFmpeg is not installed or available on PATH.")

    source_urls = payload.video_urls if payload.visual_source == "animated" else payload.image_urls
    if not source_urls:
        source_label = "animated scene videos" if payload.visual_source == "animated" else "scene images"
        raise HTTPException(status_code=400, detail=f"Video creation requires {source_label}.")

    job_id = uuid.uuid4().hex[:12]
    job_directory = VIDEO_OUTPUT_DIRECTORY / job_id
    assets_directory = job_directory / "assets"
    segments_directory = job_directory / "segments"
    assets_directory.mkdir(parents=True, exist_ok=False)
    segments_directory.mkdir(parents=True, exist_ok=True)

    source_suffix = "video" if payload.visual_source == "animated" else "image"
    source_paths = [
        assets_directory / f"scene-{index:02d}.{source_suffix}"
        for index in range(1, len(source_urls) + 1)
    ]
    voiceover_path = assets_directory / "voiceover.audio"
    music_path = assets_directory / "music.audio" if payload.music_url.strip() else None

    timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for index, (url, path) in enumerate(zip(source_urls, source_paths), start=1):
            _download_asset(client, url, path, f"scene {source_suffix} {index}")
        _download_asset(client, payload.voiceover_url, voiceover_path, "voiceover")
        if music_path:
            _download_asset(client, payload.music_url, music_path, "background music")

    width, height = ASPECT_DIMENSIONS[payload.aspect_ratio]
    total_frames = payload.duration_seconds * FPS
    base_frames, extra_frames = divmod(total_frames, len(source_paths))
    segment_paths: list[Path] = []

    for index, source_path in enumerate(source_paths):
        frame_count = base_frames + (1 if index < extra_frames else 0)
        segment_path = segments_directory / f"scene-{index + 1:02d}.mp4"
        if payload.visual_source == "animated":
            _render_animated_scene_segment(source_path, segment_path, width, height, frame_count)
        else:
            _render_scene_segment(source_path, segment_path, width, height, frame_count)
        segment_paths.append(segment_path)

    visuals_path = job_directory / "visuals.mp4"
    _concat_segments(segment_paths, job_directory / "segments.txt", visuals_path)

    assembled_path = job_directory / "video.mp4"
    _mix_audio(
        visuals_path,
        voiceover_path,
        music_path,
        assembled_path,
        payload.duration_seconds,
        payload.music_volume,
    )

    caption_result = generate_caption_style_video(
        CaptionStyleRequest(
            input_video_path=str(assembled_path),
            template_name=payload.caption_template,
            transcript_format="auto",
            language_hint=payload.language_hint,
            style_name=payload.caption_style_name,
            output_basename=f"video-{job_id}-final",
        )
    )
    output_path = Path(caption_result.output_path)
    output_url = caption_result.output_url

    return VideoGenerationResponse(
        job_id=job_id,
        title=payload.title,
        duration_seconds=payload.duration_seconds,
        aspect_ratio=payload.aspect_ratio,
        visual_source=payload.visual_source,
        width=width,
        height=height,
        scene_count=len(source_paths),
        captioned=True,
        output_path=str(output_path),
        output_url=output_url,
    )

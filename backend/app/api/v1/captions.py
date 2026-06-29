from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile

from backend.app.caption_style_generator import (
    DEFAULT_CAPTION_TEMPLATE,
    DEFAULT_TRANSCRIPT_FORMAT,
    CaptionStyleRequest,
    CaptionStyleResponse,
    generate_caption_style_video,
    save_uploaded_file,
)
from backend.app.media.cleanup import cleanup_paths

router = APIRouter()


@router.post("/generate", response_model=CaptionStyleResponse)
async def create_caption_style_video(
    request: Request,
    input_video: UploadFile = File(...),
    transcript: UploadFile | None = File(default=None),
    template_name: str = Form(DEFAULT_CAPTION_TEMPLATE),
    transcript_format: str = Form(DEFAULT_TRANSCRIPT_FORMAT),
    language_hint: str = Form(""),
    style_name: str = Form("Minimalist"),
    output_basename: str = Form(""),
) -> CaptionStyleResponse:
    uploaded_paths: list[Path] = []
    try:
        input_video_path = save_uploaded_file(
            input_video,
            "videos",
            storage=request.app.state.storage,
            settings=request.app.state.settings,
        )
        uploaded_paths.append(input_video_path)
        transcript_path = ""
        if transcript and transcript.filename:
            transcript_file_path = save_uploaded_file(
                transcript,
                "transcripts",
                storage=request.app.state.storage,
                settings=request.app.state.settings,
            )
            uploaded_paths.append(transcript_file_path)
            transcript_path = str(transcript_file_path)

        payload = CaptionStyleRequest(
            input_video_path=str(input_video_path),
            template_name=template_name,
            transcript_path=transcript_path,
            transcript_format=transcript_format,
            language_hint=language_hint,
            style_name=style_name,
            output_basename=output_basename,
        )
        return generate_caption_style_video(payload, settings=request.app.state.settings)
    except Exception:
        cleanup_paths(uploaded_paths, request.app.state.settings.local_storage_root)
        raise

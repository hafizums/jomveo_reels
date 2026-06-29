import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.caption_style_generator import (
    CaptionStyleRequest,
    CaptionStyleResponse,
    DEFAULT_CAPTION_TEMPLATE,
    DEFAULT_TRANSCRIPT_FORMAT,
    OUTPUT_DIRECTORY as CAPTION_OUTPUT_DIRECTORY,
    generate_caption_style_video,
    save_uploaded_file,
)
from backend.app.script_generator import (
    ScriptRequest,
    ScriptResponse,
    generate_video_script,
)
from backend.app.scene_generator import (
    SceneSequenceRequest,
    SceneSequenceResponse,
    generate_scene_sequence,
)
from backend.app.scene_animation_generator import (
    SceneAnimationRequest,
    SceneAnimationResponse,
    generate_scene_animations,
)
from backend.app.background_music_generator import (
    BackgroundMusicRequest,
    BackgroundMusicResponse,
    generate_background_music,
)
from backend.app.art_style_generator import (
    ArtStyleRequest,
    ArtStyleResponse,
    generate_art_style_image,
)
from backend.app.voiceover_generator import (
    VoiceoverRequest,
    VoiceoverResponse,
    generate_voiceover,
)
from backend.app.video_generator import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    generate_video,
)
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


app = FastAPI(title="WaveSpeed Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GENERATED_ROOT = Path(__file__).resolve().parents[1] / "generated"
GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
CAPTION_OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=GENERATED_ROOT), name="generated")

@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scripts/generate", response_model=ScriptResponse)
def generate_script(payload: ScriptRequest) -> ScriptResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )

    return generate_video_script(api_key, payload)


@app.post("/api/voiceovers/generate", response_model=VoiceoverResponse)
def create_voiceover(payload: VoiceoverRequest) -> VoiceoverResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )

    return generate_voiceover(api_key, payload)


@app.post("/api/background-music/generate", response_model=BackgroundMusicResponse)
def create_background_music(payload: BackgroundMusicRequest) -> BackgroundMusicResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )

    return generate_background_music(api_key, payload)


@app.post("/api/art-style/generate", response_model=ArtStyleResponse)
def create_art_style_image(payload: ArtStyleRequest) -> ArtStyleResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )

    return generate_art_style_image(api_key, payload)


@app.post("/api/art-style/scenes/generate", response_model=SceneSequenceResponse)
def create_scene_sequence(payload: SceneSequenceRequest) -> SceneSequenceResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )

    return generate_scene_sequence(api_key, payload)


@app.post("/api/videos/generate", response_model=VideoGenerationResponse)
def create_video(payload: VideoGenerationRequest) -> VideoGenerationResponse:
    return generate_video(payload)


@app.post("/api/scene-animations/generate", response_model=SceneAnimationResponse)
def create_scene_animations(payload: SceneAnimationRequest) -> SceneAnimationResponse:
    api_key = os.getenv("WAVESPEED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment.",
        )
    return generate_scene_animations(api_key, payload)


@app.post("/api/caption-style/generate", response_model=CaptionStyleResponse)
async def create_caption_style_video(
    input_video: UploadFile = File(...),
    transcript: UploadFile | None = File(default=None),
    template_name: str = Form(DEFAULT_CAPTION_TEMPLATE),
    transcript_format: str = Form(DEFAULT_TRANSCRIPT_FORMAT),
    language_hint: str = Form(""),
    style_name: str = Form("Minimalist"),
    output_basename: str = Form(""),
) -> CaptionStyleResponse:
    input_video_path = save_uploaded_file(input_video, "videos")
    transcript_path = ""

    if transcript and transcript.filename:
        transcript_path = str(save_uploaded_file(transcript, "transcripts"))

    payload = CaptionStyleRequest(
        input_video_path=str(input_video_path),
        template_name=template_name,
        transcript_path=transcript_path,
        transcript_format=transcript_format,
        language_hint=language_hint,
        style_name=style_name,
        output_basename=output_basename,
    )
    return generate_caption_style_video(payload)

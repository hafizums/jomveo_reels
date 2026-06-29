# WaveSpeed React + FastAPI Demo

A small full-stack example that uses:

- `React` for the prompt UI
- `FastAPI` for the backend API
- WaveSpeed's Nano Banana image API for styled art images
- WaveSpeed's OpenAI-compatible LLM API for short-video script generation
- WaveSpeed's text-to-speech API for voiceover generation
- WaveSpeed's music-generation API for background music
- WaveSpeed's Wan 2.2 image-to-video API for animated scene clips
- `pycaps` for local captioned-video rendering with styled burned-in subtitles

## What it does

The React app has eight flows:

- `POST /api/art-style/generate` for art-style image generation
- `POST /api/art-style/scenes/generate` for using an LLM storyboard planner to turn a script into an automatically sized sequence of scene images
- `POST /api/scripts/generate` for 60-second factual video scripts
- `POST /api/voiceovers/generate` for voiceover generation
- `POST /api/background-music/generate` for instrumental background music
- `POST /api/caption-style/generate` for uploading a video and rendering it with pycaps caption templates
- `POST /api/videos/generate` for assembling scene images, voiceover, music, and required burned-in captions into a finished MP4
- `POST /api/scene-animations/generate` for animating every generated scene image from its start frame

The FastAPI backend reads your `WAVESPEED_API_KEY`, generates styled art images through Google's Nano Banana text-to-image model, sends script requests to WaveSpeed's OpenAI-compatible chat completions endpoint with the model `openai/gpt-5.1`, generates voiceovers through ElevenLabs Multilingual V2 on WaveSpeed, creates original non-vocal background music through Mureka V9 Generate BGM, and renders captioned local videos through `pycaps`.

The script flow supports `English` and `Malay` in the app UI.

## Project structure

```text
backend/
  app/art_style_generator.py
  app/background_music_generator.py
  app/caption_style_generator.py
  app/main.py
  app/scene_generator.py
  app/scene_animation_generator.py
  app/script_generator.py
  app/voiceover_generator.py
  app/video_generator.py
  app/wavespeed_api.py
  requirements.txt
frontend/
  src/App.jsx
```

## Backend setup

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install backend dependencies:

   ```powershell
   python -m pip install -r backend\requirements.txt
   ```

   This installs `pycaps` from GitHub as part of the backend setup.

3. Add your API key:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

   Then edit `backend/.env` and set `WAVESPEED_API_KEY`.

4. Install local caption-rendering prerequisites:

   - Make sure `ffmpeg` is installed and available on your `PATH`
   - Install the browser runtime used by `pycaps`

   ```powershell
   playwright install chromium
   ```

   The first caption render may also download a Whisper model for transcription.

5. Start FastAPI:

   ```powershell
   uvicorn backend.app.main:app --reload
   ```

## Frontend setup

1. Install frontend dependencies:

   ```powershell
   cd frontend
   npm install
   ```

2. Start the React app:

   ```powershell
   npm run dev
   ```

3. Open `http://localhost:5173`

The Vite dev server proxies `/api/*` requests and `/generated/*` media to `http://127.0.0.1:8000`.

## Video Creator workflow

The Video Creator uses the latest generated assets held by the React app:

1. Generate a script.
2. Generate a voiceover from that script.
3. Generate an art-style scene sequence from that script.
4. Optionally open **Animate Scenes** to create a 5- or 8-second Wan clip from each scene's start frame.
5. Optionally generate background music.
6. In Video Creator, select still images or animated scene clips, then choose duration, aspect ratio, music level, and subtitle style.
7. Select **Create video**.

Supported aspect ratios are vertical `9:16` (`1080x1920`), landscape `16:9` (`1920x1080`), square `1:1` (`1080x1080`), and portrait `4:5` (`1080x1350`). For stills, FFmpeg applies a subtle pan and zoom. For animated scenes, it loops or trims the Wan clips to fill the selected timeline. It then mixes narration and optional background music. The assembled video is always passed through the selected `pycaps` template, so every final video includes burned-in captions.

Video jobs and their downloaded source assets are stored under `backend/generated/videos/<job-id>`. Captioned final outputs are stored under `backend/generated/captions`.

## Notes about WaveSpeed API usage

WaveSpeed's current official docs use:

- the text-to-image model `google/nano-banana/text-to-image`
- the OpenAI-compatible LLM API under `https://llm.wavespeed.ai/v1/chat/completions`
- the text-to-speech API through models such as `elevenlabs/multilingual-v2`
- the music-generation API through models such as `mureka-ai/mureka-v9/generate-bgm`
- the image-to-video model `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`
- caption rendering through the open-source `pycaps` CLI at `https://github.com/francozanardi/pycaps`

This sample uses:

- `openai/gpt-5.1` for script generation
- `openai/gpt-5.4-mini` as an affordable script-generation option
- `google/nano-banana/text-to-image` for the art-style module
- `wavespeed-ai/z-image/turbo` as an optional fast art-style model
- `elevenlabs/multilingual-v2` for voiceovers
- `google/gemini-2.5-flash/text-to-speech` as an optional multilingual voiceover model
- `mureka-ai/mureka-v9/generate-bgm` for background music
- `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` for optional 5- or 8-second animated scene clips
- `pycaps` built-in templates such as `minimalist`, `word-focus`, `line-focus`, and `explosive` for caption styling

The script generator keeps the prompt framework strict about truth mode and content niche. It targets a slow dramatic narration pace of roughly 84–99 spoken words for a 60-second clip, scaling the word range with the selected duration. The art-style generator combines a scene prompt with one of 10 predefined visual directions tuned to the story categories. It supports Nano Banana and Z Image Turbo, with a user-controlled safety-checker option powered by `wavespeed-ai/content-moderator/image`. Its scene-sequence flow uses `openai/gpt-5.4-mini` as a storyboard director: it reads the full script, decides how many visual beats the selected duration needs, and writes a standalone production prompt for each scene with continuity instructions. Z Image Turbo scene requests run sequentially to avoid burst-rate failures. The voiceover generator supports ElevenLabs tuning controls as well as Gemini 2.5 Flash TTS with a selectable language locale, named speaker, and one of its 30 documented voices. The background music generator uses Mureka's documented BGM flow with prompt-based non-vocal music generation and optional multiple variations. The caption module lets you upload a video from the browser, choose from multiple `pycaps` templates, and optionally provide an `srt`, `vtt`, `whisper_json`, or `pycaps_json` transcript. The Video Creator downloads the latest generated assets and uses FFmpeg plus required `pycaps` rendering to create the final video.

The storyboard planner also writes a constrained motion prompt for every image. Animate Scenes sends only that image through Wan's `image` start-frame field; it never sends `last_image`. Video Creator can then assemble either the still images or their corresponding animated clips.

For script generation, the selected language is passed into the prompt so the model writes the output in that language. For voiceovers, the selected gender and style act as app-level selectors that map to valid ElevenLabs `voice_id` values from WaveSpeed's official voice list. For background music, the presets are designed for original non-vocal underscore tracks; review final usage rights and platform terms before commercial publishing. For caption rendering, the output video is written under `backend/generated/captions` and served back through `/generated/captions/...`.

If you still see `403 Forbidden`, that is usually account-side rather than code-side. Make sure your WaveSpeed key is active and your account is allowed to use the requested model or LLM endpoint.
## Backend quality checks

Copy `backend/.env.example` to `backend/.env` and set `WAVESPEED_API_KEY` for
provider-backed endpoints. Start the API from the repository root:

```bash
uvicorn backend.app.main:app --reload
```

Run the backend quality checks with:

```bash
python -m pytest backend/tests
python -m ruff check backend/app backend/tests
python -m ruff format --check backend/app backend/tests
```

## Persistent generation jobs

Persistent job endpoints are available for every JSON generation flow:

- `POST /api/jobs/scripts/generate`
- `POST /api/jobs/voiceovers/generate`
- `POST /api/jobs/background-music/generate`
- `POST /api/jobs/art-style/generate`
- `POST /api/jobs/art-style/scenes/generate`
- `POST /api/jobs/scene-animations/generate`
- `POST /api/jobs/videos/generate`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs?limit=20`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/recover-stale`

The existing synchronous endpoints remain available. Multipart caption uploads
remain synchronous until uploaded-file storage is hardened.

The local defaults use SQLite and execute jobs inline. Configure the job system
in `backend/.env` when Redis Queue execution is needed:

```env
DATABASE_URL=sqlite:///backend/generated/jomveo.db
QUEUE_BACKEND=inline
REDIS_URL=redis://localhost:6379/0
JOB_DEFAULT_TIMEOUT_SECONDS=1800
JOB_MAX_ATTEMPTS=3
JOB_RETRY_BACKOFF_SECONDS=30
JOB_STALE_AFTER_SECONDS=900
JOB_WORKER_ID=local-worker
```

Retryable provider, timeout, bad-response, and unexpected worker errors move a
job to `retrying` until its attempt limit is reached. The recovery endpoint
requeues due retries and recovers stale running jobs. Authentication must be
added to this administrative endpoint before a public production deployment.

Inline mode executes the initial attempt in the API process. Retries deliberately
wait for `POST /api/jobs/recover-stale` to avoid recursive inline execution. RQ
mode also relies on recovery for delayed retries; an automatic scheduler is not
included yet. Progress is coarse for scene and video jobs until generator-level
callbacks are introduced.

Production environments must run `alembic upgrade head` before starting the API.
Automatic table creation is limited to local, development, and test environments.

Common backend commands:

```bash
# Run API
uvicorn backend.app.main:app --reload

# Run tests
python -m pytest backend/tests

# Run RQ worker when QUEUE_BACKEND=rq
python -m backend.app.workers.rq_worker

# Run migrations
alembic upgrade head
```

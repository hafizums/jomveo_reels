# WaveSpeed React + FastAPI Demo

A small full-stack example that uses:

- `React` for the prompt UI
- `FastAPI` for the backend API
- WaveSpeed's Z Image Turbo API for styled art images
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

The FastAPI backend reads your `WAVESPEED_API_KEY`, generates styled art images through Z Image Turbo, sends script requests to WaveSpeed's OpenAI-compatible chat completions endpoint with the model `openai/gpt-5.1`, generates voiceovers through Gemini 2.5 Flash TTS on WaveSpeed, creates original non-vocal background music through Mureka V9 Generate BGM, and renders captioned local videos through `pycaps`.

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

   To transcribe through the OpenAI API instead of relying on local transcription,
   configure the optional backend-only settings described below.

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

## Optional OpenAI caption transcription

Caption rendering still runs locally through `pycaps` and FFmpeg. When no transcript is
uploaded, the backend can first call OpenAI transcription and save an SRT or VTT file
under `backend/generated/captions/transcripts`. Uploaded transcripts always take
priority over automatic transcription.

Add these values only to `backend/.env`; never expose `OPENAI_API_KEY` through a
`VITE_*` variable:

```env
OPENAI_API_KEY=sk-...
TRANSCRIPTION_PROVIDER=openai
TRANSCRIPTION_MODEL=whisper-1
TRANSCRIPTION_OUTPUT_FORMAT=srt
TRANSCRIPTION_PROMPT=
TRANSCRIPTION_TIMEOUT_SECONDS=600
```

`whisper-1` is the default because it supports timestamped `srt` and `vtt` responses
that `pycaps` can consume directly. Leave `TRANSCRIPTION_PROVIDER=none` to preserve the
existing caption behavior without an OpenAI request. `pycaps`, its browser runtime, and
FFmpeg remain required to render the final captioned MP4.

Start both services for a manual UI test:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend
npm run dev
```

Open `/generate`, choose **Caption Style**, upload a short video containing speech,
leave the transcript upload empty, and submit. Confirm an SRT transcript is created and
the captioned MP4 is available. The same flow can be tested directly:

```bash
curl -X POST "http://localhost:8000/api/caption-style/generate" \
  -F "input_video=@sample.mp4" \
  -F "template_name=minimalist" \
  -F "transcript_format=srt" \
  -F "language_hint=ms" \
  -F "style_name=Minimalist"
```

With OpenAI transcription enabled, the response includes the generated
`transcript_path`, uses `transcript_format=srt`, includes `--transcript` in the pycaps
command, and returns the captioned `output_url`.

Final video generation returns a `processing_timings` breakdown for asset downloads,
scene rendering, scene merging, audio mixing, OpenAI transcription, caption burning, and
total elapsed time. The Video Creator displays these timings after a successful render.
Video Creator also exposes pycaps quality levels: `low` (fastest), `middle` (the
backward-compatible default), `high`, and `very_high` (slowest). Lower quality can reduce
caption-render time at the cost of output compression quality.
When the video request includes the script used for its voiceover, auto-generated SRT/VTT
captions are compared with that script and unmatched trailing cues are removed
conservatively. Uploaded transcripts are never filtered.

## Notes about WaveSpeed API usage

WaveSpeed's current official docs use:

- the text-to-image model `wavespeed-ai/z-image/turbo`
- the OpenAI-compatible LLM API under `https://llm.wavespeed.ai/v1/chat/completions`
- the text-to-speech model `google/gemini-2.5-flash/text-to-speech`
- the music-generation API through models such as `mureka-ai/mureka-v9/generate-bgm`
- the image-to-video model `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`
- caption rendering through the open-source `pycaps` CLI at `https://github.com/francozanardi/pycaps`

This sample uses:

- `openai/gpt-5.1` for script generation
- `openai/gpt-5.4-mini` as an affordable script-generation option
- `wavespeed-ai/z-image/turbo` for the art-style module
- `google/gemini-2.5-flash/text-to-speech` for multilingual voiceovers
- `mureka-ai/mureka-v9/generate-bgm` for background music
- `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` for optional 5- or 8-second animated scene clips
- `pycaps` built-in templates such as `minimalist`, `word-focus`, `line-focus`, and `explosive` for caption styling

The script generator keeps the prompt framework strict about truth mode and content niche. It targets a slow dramatic narration pace of roughly 84–99 spoken words for a 60-second clip, scaling the word range with the selected duration. The art-style generator combines a scene prompt with one of 10 predefined visual directions tuned to the story categories. It uses Z Image Turbo with a user-controlled safety-checker option powered by `wavespeed-ai/content-moderator/image`. Its scene-sequence flow uses `openai/gpt-5.4-mini` as a storyboard director: it reads the full script, decides how many visual beats the selected duration needs, and writes a standalone production prompt for each scene with continuity instructions. Z Image Turbo scene requests run sequentially to avoid burst-rate failures. The voiceover generator uses Gemini 2.5 Flash TTS with a selectable language locale, named speaker, and one of its 30 documented voices. The background music generator uses Mureka's documented BGM flow with prompt-based non-vocal music generation and optional multiple variations. The caption module lets you upload a video from the browser, choose from multiple `pycaps` templates, and optionally provide an `srt`, `vtt`, `whisper_json`, or `pycaps_json` transcript. The Video Creator downloads the latest generated assets and uses FFmpeg plus required `pycaps` rendering to create the final video.

The storyboard planner also writes a constrained motion prompt for every image. Animate Scenes sends only that image through Wan's `image` start-frame field; it never sends `last_image`. Video Creator can then assemble either the still images or their corresponding animated clips.

For script generation, the selected language is passed into the prompt so the model writes the output in that language. For voiceovers, the selected language, speaker name, and Gemini voice are sent to WaveSpeed's text-to-speech model. For background music, the presets are designed for original non-vocal underscore tracks; review final usage rights and platform terms before commercial publishing. For caption rendering, the output video is written under `backend/generated/captions` and served back through `/generated/captions/...`.

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
remain synchronous while job-owned upload retention and cleanup are finalized.

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
requeues due retries and recovers stale running jobs. Recovery and cancellation
are administrative operations protected by the API-key authentication described below.

Inline mode executes the initial attempt in the API process. Retries deliberately
wait for `POST /api/jobs/recover-stale` to avoid recursive inline execution. RQ
mode also relies on recovery for delayed retries; an automatic scheduler is not
included yet. Progress is coarse for scene and video jobs until generator-level
callbacks are introduced.

Production environments must run `alembic upgrade head` before starting the API.
Automatic table creation is limited to local, development, and test environments.

## Local media storage and validation

Generated media and validated uploads use the local storage backend under
`backend/generated` by default and are served from `/generated`. Storage keys reject
absolute paths, traversal, Windows drive paths, and unsafe path characters. Production
deployments should eventually move public media serving behind object storage and a CDN.

Uploads default to a 100 MB limit. Caption video uploads accept MP4, WebM, and QuickTime
files. Transcript uploads accept `.srt`, `.vtt`, `.json`, and `.txt`. Declared content
types, extensions, and basic file signatures are checked before files are persisted.

Remote video-assembly assets are limited to HTTP and HTTPS, bounded to 100 MB, and
validated by media signature. URLs with credentials are rejected. DNS results in private,
loopback, link-local, multicast, reserved, or unspecified networks are blocked on every
redirect unless private downloads are explicitly enabled.

```env
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=generated
PUBLIC_GENERATED_URL_PREFIX=/generated
MAX_UPLOAD_BYTES=104857600
MAX_REMOTE_ASSET_BYTES=104857600
REMOTE_DOWNLOAD_TIMEOUT_SECONDS=60
ALLOW_PRIVATE_NETWORK_DOWNLOADS=false
ALLOWED_REMOTE_ASSET_SCHEMES='["https","http"]'
```

`POST /api/caption-style/generate` remains synchronous. Its uploads are now safely
persisted, but the optional caption job route is deferred until job-specific retention
and cleanup policies are available.

## Administrative authentication

Administrative API-key authentication protects internal controls while public/demo
generation and job creation/status routes remain unchanged. Configure one or more keys
in `backend/.env`; never commit real keys:

```env
ADMIN_AUTH_ENABLED=true
ADMIN_API_KEYS='["replace-with-a-random-admin-key"]'
USER_AUTH_ENABLED=false
DEMO_USER_ENABLED=true
DEMO_USER_EMAIL=demo@jomveo.local
```

Send the key using the preferred bearer header:

```text
Authorization: Bearer <admin-api-key>
```

Local tooling may instead use `X-Admin-API-Key: <admin-api-key>`. The protected routes
are:

- `POST /api/jobs/recover-stale`
- `POST /api/jobs/{job_id}/cancel`
- `GET /api/provider/wavespeed/status?live=true`

Public `GET /api/provider/wavespeed/status` diagnostics do not require authentication.
The live form still obeys `ALLOW_PROVIDER_LIVE_CHECKS` and never runs model inference.

For isolated local development, authentication can be disabled with
`ADMIN_AUTH_ENABLED=false`. Never use that setting in production. Production startup
fails when admin authentication is enabled without at least one configured key.

This API-key mechanism is an admin foundation, not end-user identity. A future milestone
can replace API keys with browser sessions or JWT-based login.

## Users, projects, and job ownership

The backend now has persistent users, hashed API-key records, projects, memberships,
owned jobs, and audit history. Raw user API keys are never stored: only a SHA-256 hash
and a short display prefix are retained. User keys can be supplied through either
`Authorization: Bearer <user-api-key>` or `X-User-API-Key: <user-api-key>`. Configured
admin keys continue to work and have system-wide access.

Until the frontend has login support, `DEMO_USER_ENABLED=true` resolves unauthenticated
job requests to `demo@jomveo.local` and its Demo Project. This preserves the existing
generation flow and response shapes. Demo mode is unsafe for a public multi-user
production deployment because unauthenticated visitors share one identity and project;
disable it when user authentication is deployed.

Project routes are available under `/api/projects`, including CRUD, membership
management, and `GET /api/projects/{project_id}/jobs`. Existing job creation routes may
select a project with `X-Project-ID`. Without that header, demo requests are attached to
the Demo Project. Job list/detail responses are scoped to the authenticated user's own
jobs and accessible projects; system admins can inspect all jobs.

Project permissions are:

- `owner`: read, update, delete, manage members, create jobs, and read jobs.
- `admin`: read, update, manage non-owner membership, create jobs, and read jobs.
- `editor`: read the project and create/read jobs.
- `viewer`: read the project and its jobs.

Project creation automatically makes the creating user an owner. API keys can currently
be seeded by backend tests or trusted development code using `UserRepository.create()`
and `APIKeyRepository.create(raw_key, name, role, user_id)`; the raw key is supplied and
managed by that caller and is not recoverable from the database.

Persistent audit entries record project and membership changes, job creation and admin
job actions, provider live-status checks, and API-key acceptance/rejection. Audit
metadata is allow-listed and excludes raw keys, full prompts, scripts, provider payloads,
and provider responses. System admins can inspect recent entries with `GET /api/audit`
and optionally filter by `project_id`.

Production rejects disabled admin authentication and the documented change-me admin
key. Future work should add frontend login, session/JWT authentication, project
dashboards, per-project billing, and per-project object storage.

## Project billing and quotas

Project jobs use an integer credit ledger; **1 credit represents 1 US cent** and 100
credits represent USD 1.00. These credits currently use conservative internal placeholder
estimates, not authoritative WaveSpeed prices. Real provider price synchronization and
post-run reconciliation remain future work.

When billing is required, job creation estimates its cost, checks daily/monthly job and
credit quotas plus concurrent-job limits, and reserves credits atomically with the job.
A successful job consumes its reservation. Exhausted failures and cancellations release
it, while retries retain the original reservation. Idempotent job reuse never reserves a
second time. Provider cost records retain the estimate and current placeholder actual
cost for later reconciliation.

Demo requests bypass credit requirements by default when
`DEMO_BILLING_ENABLED=false`, preserving the existing frontend workflow. Set it to true
to test billing against the Demo Project. `BILLING_ENABLED=false` disables reservations
globally while retaining ownership behavior.

Billing routes are:

- `GET /api/projects/{project_id}/billing`
- `GET /api/projects/{project_id}/billing/transactions`
- `GET /api/projects/{project_id}/billing/usage`
- `GET /api/projects/{project_id}/quotas`
- `POST /api/projects/{project_id}/billing/top-up` (system admin)
- `POST /api/projects/{project_id}/billing/reconcile` (system admin)
- `PATCH /api/projects/{project_id}/quotas` (system admin)

Top-ups increase balance and lifetime purchased credits. Every reserve, consume, release,
and top-up is appended to the transaction ledger, and billing/quota actions are also
written to the safe audit log. Future billing milestones should add real provider price
sync, payment gateways such as Stripe/Billplz/ToyyibPay, invoices, and a project billing
dashboard.

## Temporary provider assets

WaveSpeed-generated files remain hosted by the provider for the MVP and may expire after
the configured retention window. Availability is not guaranteed. Generated files are
temporarily hosted by the provider; please download them before the link expires.

Asset metadata is available from `GET /api/projects/{project_id}/assets`,
`GET /api/projects/{project_id}/assets/{asset_id}`, and `GET /api/jobs/{job_id}/assets`.
Statuses are `available`, `expiring_soon`, or `expired`. Configure the assumed window with
`PROVIDER_ASSET_RETENTION_DAYS` and the warning threshold with
`PROVIDER_ASSET_EXPIRING_SOON_HOURS`. The backend stores URLs and safe metadata only: it
does not download, proxy, or durably store provider output. S3/R2/CDN storage is
intentionally deferred to a future milestone.

## Frontend workspace dashboard

The frontend now exposes project selection/creation, project jobs and status polling,
billing balances and quota usage, transaction history, and temporary asset warnings.
Copy `frontend/.env.example` to `frontend/.env` and configure:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USER_API_KEY=
VITE_ADMIN_API_KEY=
VITE_DEFAULT_PROJECT_ID=
```

Without a user key, the frontend relies on backend demo mode. The selected project is
stored under `jomveo.selectedProjectId`. A configured admin key reveals the local manual
top-up form; payments and invoices are not implemented. Existing synchronous generator
forms remain available in the routed generator studio.

The frontend workspace uses lightweight client-side routes. Open `/dashboard` for the
project overview and `/generate` for all synchronous and persistent generator controls.
Open `/create` for the guided Create New Series workflow; `/series/new` redirects there.
The MVP stores series drafts in the browser and queues the configured first script job,
then directs advanced production work to `/generate`.
Selected-project jobs, assets, and billing are available under `/projects/{project_id}`,
and individual jobs open at `/jobs/{job_id}`. The top navigation keeps these pages
connected while preserving `jomveo.selectedProjectId` across reloads.

## Frontend baseline tests

Run `cd frontend`, then `npm run test` for Vitest unit/component coverage and
`npm run test:e2e` for Playwright browser characterization. Vitest covers API/header
helpers, persistent job payload builders, and focused dashboard components. Playwright
mocks backend APIs and protects dashboard behavior, project persistence, job
headers/details, asset warnings, and legacy generator tabs before future refactors.
The dashboard includes explicit loading, empty, warning, error, and submission states;
Vitest checks these component states while Playwright covers browser and mobile regressions.

Every supported JSON generator also has a secondary project-job control. These controls
reuse the selected dashboard project, send `X-Project-ID` and an idempotency key, refresh
the dashboard after acceptance, and leave the original synchronous generation buttons
unchanged. Caption rendering remains synchronous because it has no persistent job route.

## Housekeeping audit

Run `python -m backend.app.housekeeping.outdated_info_audit` for a read-only Markdown
report covering route documentation, environment examples, frontend API usage,
provider/model/pricing and retention assumptions, maintenance markers, dates, milestone
references, README sections, and tracked generated artifacts. JSON is available with
`--format json`. Use `--fail-on high` in CI to reject serious documentation or
configuration drift. The command never rewrites files or contacts external services.

## WaveSpeed provider integration

Model inference uses the official
[WaveSpeed Python SDK](https://github.com/WaveSpeedAI/wavespeed-python)
(`>=1.0.9,<2`) by default.
The provider wrapper keeps SDK response normalization and safe exception mapping out of
the generator modules. Set the provider mode in `backend/.env`:

```env
WAVESPEED_PROVIDER_MODE=sdk
WAVESPEED_SDK_TIMEOUT_SECONDS=36000
WAVESPEED_SDK_POLL_INTERVAL_SECONDS=1
WAVESPEED_SDK_ENABLE_SYNC_MODE=false
ALLOW_PROVIDER_LIVE_CHECKS=false
PROVIDER_SMOKE_TEST_MODEL=wavespeed-ai/z-image/turbo
PROVIDER_SMOKE_TEST_TIMEOUT_SECONDS=120
```

Current provider classification:

- SDK run-model adapter: art-style images, image moderation, voiceovers, background
  music, scene images, and scene animations.
- Legacy OpenAI-compatible HTTP: script generation and scene planning. The official SDK
  exposes model run/upload APIs, but not the separate `/v1/chat/completions` contract.
- Local processing: video assembly and captions do not call WaveSpeed.

For rollback of model inference only, use:

```env
WAVESPEED_PROVIDER_MODE=legacy_http
```

The legacy mode retains the previous submit/poll implementation. Chat-completion flows
remain legacy in either mode. The SDK serverless-worker features are intentionally not
used by this application.

### Provider diagnostics and observability

`GET /api/provider/wavespeed/status` reports the selected provider mode, installed SDK
version, whether a key is configured, and the legacy chat-completions classification. It
does not expose the key and does not contact WaveSpeed by default. `?live=true` is also
local-only unless `ALLOW_PROVIDER_LIVE_CHECKS=true` and a key is configured; even then it
only verifies SDK client construction and does not run a paid model.

Each persistent job records a `ProviderRun` with `started_at`, `completed_at`,
`duration_ms`, `external_request_id`, `sdk_version`, and `provider_mode`. Request and
response summaries contain only operational metadata such as job type, model, mode,
result availability, and output count. API keys, full prompts/scripts, payloads, and raw
provider responses are deliberately excluded. Concurrent scene image workers create an
independent provider client per scene; Z Image Turbo retains its sequential behavior.

The normal backend suite is fully offline and skips provider smoke tests:

```bash
python -m pytest backend/tests
```

To deliberately run the single real-provider staging smoke test, configure a low-cost
model if needed and opt in explicitly:

```bash
RUN_LIVE_PROVIDER_TESTS=1 WAVESPEED_API_KEY=... python -m pytest backend/tests/live -m live_provider
```

PowerShell:

```powershell
$env:RUN_LIVE_PROVIDER_TESTS="1"
$env:WAVESPEED_API_KEY="..."
python -m pytest backend/tests/live -m live_provider
```

The live smoke test performs one image generation and may consume WaveSpeed credits. It
is never required for the offline quality checks.

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

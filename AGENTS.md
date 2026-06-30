# AGENTS.md — Jomveo Reels

A comprehensive guide for AI agents (and developers) working in this codebase.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Tech Stack](#3-tech-stack)
4. [Architecture](#4-architecture)
5. [Backend](#5-backend)
6. [Frontend](#6-frontend)
7. [Design System](#7-design-system)
8. [Data Flow — Generate vs Queue](#8-data-flow--generate-vs-queue)
9. [Job System](#9-job-system)
10. [Environment Variables](#10-environment-variables)
11. [Running Locally](#11-running-locally)
12. [Testing](#12-testing)
13. [Code Style Rules](#13-code-style-rules)
14. [Common Patterns & Gotchas](#14-common-patterns--gotchas)

---

## 1. Project Overview

Jomveo is a **short-form video studio** that chains AI generators together to produce complete vertical videos from a text niche description. The pipeline is:

```
Script → Voiceover → Art (scenes) → Animate → Background Music → Video assembly → Captions
```

- **Generate** (synchronous): any tab's primary violet button calls the generator API directly and shows the result inline. No project needed. No credits consumed.
- **Save to Project** (asynchronous): the dashed card at the bottom of every form sends the same payload to the job queue. The job runs server-side, is tracked in the Dashboard, and consumes billing credits.

---

## 2. Repository Layout

```
jomveo/
├── backend/                    # Python / FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app factory (create_app)
│   │   ├── api/v1/             # HTTP route handlers (one file per domain)
│   │   │   ├── router.py       # APIRouter that wires all sub-routers
│   │   │   ├── jobs.py         # Job queue endpoints (POST /api/jobs/*/generate)
│   │   │   ├── scripts.py      # POST /api/scripts/generate (sync)
│   │   │   ├── voiceovers.py   # POST /api/voiceovers/generate (sync)
│   │   │   ├── art_style.py    # POST /api/art-style/generate (sync)
│   │   │   ├── music.py        # POST /api/background-music/generate (sync)
│   │   │   ├── scenes.py       # POST /api/art-style/scenes/generate (sync)
│   │   │   ├── videos.py       # POST /api/videos/generate (sync)
│   │   │   ├── captions.py     # POST /api/caption-style/generate (sync, multipart)
│   │   │   ├── projects.py     # CRUD for projects
│   │   │   ├── assets.py       # Asset tracking
│   │   │   ├── billing.py      # Credits, top-up, usage, quotas
│   │   │   ├── health.py       # GET /api/health
│   │   │   ├── identity.py     # GET /api/me
│   │   │   ├── audit.py        # Admin audit log
│   │   │   └── provider.py     # Provider smoke-test / status
│   │   ├── application/        # Application services (jobs, billing, projects)
│   │   ├── auth/               # API key auth (admin + user + demo)
│   │   ├── core/               # config.py (Settings), errors, logging, middleware
│   │   ├── db/                 # SQLAlchemy models + session factory
│   │   ├── domain/             # Domain-level errors
│   │   ├── infrastructure/     # WaveSpeed provider client + observability
│   │   ├── repositories/       # DB repository pattern (jobs, projects, assets…)
│   │   ├── workers/
│   │   │   ├── runner.py       # execute_job() — the universal job executor
│   │   │   └── rq_worker.py    # RQ worker entrypoint
│   │   ├── storage/            # LocalStorageBackend
│   │   ├── script_generator.py
│   │   ├── voiceover_generator.py
│   │   ├── art_style_generator.py
│   │   ├── scene_generator.py
│   │   ├── scene_animation_generator.py
│   │   ├── background_music_generator.py
│   │   ├── video_generator.py
│   │   ├── caption_style_generator.py
│   │   └── wavespeed_api.py    # Low-level WaveSpeed REST helpers
│   ├── tests/                  # pytest test suite
│   ├── .env                    # Local secrets (not committed)
│   ├── .env.example            # Canonical list of all env vars
│   └── requirements.txt
├── frontend/                   # React SPA (Vite)
│   └── src/
│       ├── App.jsx             # Root component — all state, all handlers
│       ├── styles.css          # Global design system (single stylesheet)
│       ├── components/         # Dumb UI components
│       ├── routes/             # Page-level route components
│       ├── lib/
│       │   ├── api.js          # fetch wrapper + backend client object
│       │   └── jobPayloads.js  # Payload builders for every job type
│       └── data/               # Static presets/options arrays
├── alembic/                    # DB migration scripts
├── pyproject.toml              # pytest + ruff config
└── README.md
```

---

## 3. Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.116 |
| ASGI server | Uvicorn |
| Database | SQLAlchemy 2.x + SQLite (dev) / Postgres (prod) |
| Migrations | Alembic |
| Job queue | `inline` (default dev) or RQ + Redis |
| AI provider | WaveSpeed SDK + LLM base URL |
| Captions | pycaps (local ffmpeg-based renderer) |
| Linter | Ruff (line-length=100, target py310) |
| Tests | pytest |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 (JSX) |
| Build tool | Vite |
| Router | react-router-dom v6 |
| Styling | Vanilla CSS (`styles.css`) — no Tailwind |
| HTTP | Native `fetch` |
| State | useState / useCallback in `App.jsx` (no external store) |
| Tests | Vitest + React Testing Library |

---

## 4. Architecture

### Request paths

```
Browser
  │
  ├─ Generate (sync)   → POST /api/{resource}/generate
  │                        → generator module → WaveSpeed → JSON result
  │
  └─ Save to Project   → POST /api/jobs/{kind}/generate
                           → job created in DB (status=queued)
                           → queue.enqueue(execute_job)
                           → worker: claim → call generator → mark_completed
                           → BillingService.consume() → AssetService.register()
```

### Key boundaries
- All **sync generators** live in `backend/app/*_generator.py`. They are plain Python functions that call WaveSpeed.
- The **job runner** (`workers/runner.py:execute_job`) calls those same generator functions. A job definition maps a `job.type` string (e.g. `"script.generate"`) to its handler via `application/jobs/registry.py`.
- **Auth** is per-request via HTTP headers: `X-Admin-API-Key` (admin operations) and `X-User-API-Key` (user operations). The demo mode bypasses user auth automatically.
- **Billing** is checked on job creation (`JobService.create_job`) and consumed on job completion (`BillingService.consume`).

---

## 5. Backend

### Adding a new generator

1. Create `backend/app/my_generator.py` with a `MyRequest(BaseModel)` + a handler function.
2. Create `backend/app/api/v1/my_route.py` with a FastAPI router and two endpoints:
   - Sync: `POST /api/my-resource/generate` (calls handler directly)
   - Job: wired via `jobs.py` using an existing pattern
3. Register the job type in `backend/app/application/jobs/registry.py`.
4. Include the router in `backend/app/api/v1/router.py`.

### Settings (`core/config.py`)
- All settings are Pydantic `BaseSettings`, loaded from `backend/.env`.
- Add new settings here. Use `Field(default=...)` with a docstring.
- Access via `get_settings()` (cached with `@lru_cache`), or from `request.app.state.settings` in route handlers.

### Database
- Models live in `backend/app/db/models.py`.
- Never call `create_tables()` in production — use Alembic migrations (`alembic upgrade head`).
- Sessions are managed by `session_factory()` context manager. **Always** `session.commit()` explicitly inside `with session_factory() as session:` blocks.

### Auth
- `require_principal` → accepts admin key, user key, or demo user (if enabled).
- `require_admin` → admin key only.
- Auth is disabled per-key via `ADMIN_AUTH_ENABLED` / `USER_AUTH_ENABLED`.
- Project isolation: `X-Project-ID` header binds a job/asset to a project.

### Error codes (retryable vs not)
Retryable error codes that trigger a job retry:
```
provider_error, provider_timeout_error, provider_bad_response_error, internal_server_error
```
Non-retryable: `validation_error`, `provider_auth_error`, `provider_forbidden_error`.

### Queue backends
- `QUEUE_BACKEND=inline` (default): jobs run synchronously in the request thread. Good for development.
- `QUEUE_BACKEND=rq`: jobs are enqueued into Redis. Start a worker with `python -m backend.app.workers.rq_worker`.

---

## 6. Frontend

### State management
All application state lives in `App.jsx`. There is **no Redux / Zustand / Context**. Every generator section receives its state slices and handlers as explicit props.

Key state groups:
```
scriptForm/scriptResult/scriptError/scriptLoading
voiceForm/voiceResult/voiceError/voiceLoading
artForm/artResult/artSceneResult/artError/artLoading/artSceneLoading
musicForm/musicResult/musicError/musicLoading
sceneAnimationForm/sceneAnimationResult/sceneAnimationError/sceneAnimationLoading
captionForm/captionFiles/captionResult/captionError/captionLoading
videoForm/videoResult/videoError/videoLoading
queueLoading/queueMessage/queueError          ← shared across all queue actions
activeTab                                      ← which pipeline step is shown
selectedProjectId                             ← persisted to localStorage
```

### Adding a new form field
1. Add to the relevant `initialXxxForm` const in `App.jsx`.
2. Add an `updateXxxField` handler (or extend the existing one).
3. Add the `<label>` + input in the section component.
4. Update the payload builder in `lib/jobPayloads.js` if it should be queued.

### API client (`lib/api.js`)
```js
// Sync generate (no project, no credits):
await fetch('/api/scripts/generate', { method: 'POST', body: JSON.stringify(form) })

// Async job (uses project + credits):
await backend.createJob('scripts', payload, projectId)
// → POST /api/jobs/scripts/generate with X-Project-ID header + Idempotency-Key
```

### Job payload builders (`lib/jobPayloads.js`)
Every `buildXxxJobPayload()` function returns `null` if prerequisites are missing. `resolveQueueConfiguration()` dispatches by `activeTab` and returns `[kind, payload]` or `null`.

### Routing (react-router-dom v6)
| Path | Component |
|---|---|
| `/` | Redirects to `/dashboard` |
| `/dashboard` | `DashboardPage` |
| `/generate` | `GeneratePage` (contains the pipeline workspace) |
| `/projects/:projectId` | `ProjectPage` |
| `/projects/:projectId/jobs` | `ProjectJobsPage` |
| `/projects/:projectId/assets` | `AssetsPage` |
| `/projects/:projectId/billing` | `BillingPage` |
| `/jobs/:jobId` | `JobDetailPage` |

---

## 7. Design System

All styles live in a **single file**: `frontend/src/styles.css`. There is **no component-level CSS** and **no Tailwind**. Use the existing CSS custom properties and utility classes.

### Design tokens (CSS variables)
```css
--color-bg:      #f4f5fa   /* page background */
--color-surface: #ffffff   /* card/panel background */
--accent-violet: #7c3aed   /* primary brand */
--accent-indigo: #4f46e5   /* secondary brand */
--grad-primary:  linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)
--shadow-violet: 0 8px 28px rgba(124,58,237,0.22)
--radius-md:     14px
--radius-lg:     20px
--radius-xl:     28px
--trans-normal:  220ms cubic-bezier(0.4, 0, 0.2, 1)
```

### Key layout classes
| Class | Purpose |
|---|---|
| `.page` | Max-width wrapper (1280px, horizontal padding) |
| `.pipeline-shell` | Two-column grid: sidebar (220px) + content |
| `.pipeline` | Left sidebar stepper card |
| `.pipeline-step` | Individual step button (`.is-active`, `.is-done`) |
| `.workspace` | Two-column form + result panel grid |
| `.panel` | Glass surface card with shadow and top accent line |
| `.form-panel` | Flex-column form with consistent label/input styling |
| `.stack` | Section animation wrapper |
| `.preset-grid` | Auto-fill preset card grid |
| `.project-action-card` | "Save to Project" dashed card at form bottom |
| `.empty-state` | Dashed placeholder region inside result panels |

### Button types
- **Primary** (`button`): violet gradient, `box-shadow: --shadow-violet`. Used for "Generate".
- **Secondary** (`.secondary-button`): transparent background, subtle border. Used for "Pull latest script".
- **Project action** (`.project-action-btn`): outlined violet, sits inside `.project-action-card`.

### Typography
Font: **Inter** (loaded from Google Fonts in `index.html`). Use `var(--text-sm)` / `var(--text-base)` etc., not raw `px` values.

### Adding new styles
Append to `styles.css` in the relevant section. Never write inline `style={{}}` unless it's a dynamic runtime value (e.g. range slider percent).

---

## 8. Data Flow — Generate vs Queue

```
User fills form
      │
      ├─ Clicks "Generate X"  (violet primary button)
      │       │
      │       └─ handleXxxSubmit() in App.jsx
      │               └─ fetch('/api/xxx/generate', { POST, body: form })
      │                       └─ result set into state → shown in result panel
      │
      └─ Clicks "Save to Project"  (project-action-card button)
              │
              └─ queueProjectJob() in App.jsx
                      ├─ resolveQueueConfiguration() → [kind, payload]
                      └─ backend.createJob(kind, payload, projectId)
                              └─ POST /api/jobs/{kind}/generate
                                     X-Project-ID: <projectId>
                                     Idempotency-Key: <uuid>
                                  └─ returns { job_id }
                                  └─ Job tracked in Dashboard → Project Jobs
```

**The payloads are identical for both paths.** The difference is only:
- Sync: called directly, result returned in response.
- Async: accepted immediately, executed by worker, result stored in DB.

---

## 9. Job System

### Job lifecycle
```
queued → running → completed
                └→ retrying → running → … (up to max_attempts)
                └→ failed
                └→ cancelled
```

### Job types (registered in `application/jobs/registry.py`)
| Job type string | Generator module |
|---|---|
| `script.generate` | `script_generator.py` |
| `voiceover.generate` | `voiceover_generator.py` |
| `background_music.generate` | `background_music_generator.py` |
| `art_style.generate` | `art_style_generator.py` |
| `scene_sequence.generate` | `scene_generator.py` |
| `scene_animation.generate` | `scene_animation_generator.py` |
| `video.generate` | `video_generator.py` |

### Progress tracking
`runner.py` calls `_initial_progress_total()` before execution:
- `scene_animation.generate`: `len(scenes)` (one step per scene clip)
- `video.generate`: 5 (fixed)
- Everything else: 1

### Asset retention
Generated files are stored in `backend/generated/` (local). Provider-side asset URLs expire after `PROVIDER_ASSET_RETENTION_DAYS` (default 7 days). The UI shows an "expiring soon" warning within the last 24 hours (`PROVIDER_ASSET_EXPIRING_SOON_HOURS`).

---

## 10. Environment Variables

Create `backend/.env` by copying `backend/.env.example`. Required values:

| Variable | Required | Notes |
|---|---|---|
| `WAVESPEED_API_KEY` | ✅ Yes | Your WaveSpeed key |
| `ADMIN_API_KEYS` | ✅ Yes | JSON array, e.g. `'["my-secret-key"]'` |
| `DATABASE_URL` | No | Defaults to SQLite at `backend/generated/jomveo.db` |
| `QUEUE_BACKEND` | No | `inline` (default) or `rq` |
| `REDIS_URL` | Only if RQ | `redis://localhost:6379/0` |
| `APP_ENV` | No | `development` disables migration enforcement |
| `BILLING_ENABLED` | No | `true` by default |
| `DEMO_USER_ENABLED` | No | `true` enables auth-free demo access |
| `CORS_ALLOWED_ORIGINS` | No | JSON array of allowed frontend origins |

Frontend env vars (in `frontend/.env`):

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Backend URL if not proxied (empty = same origin) |
| `VITE_ADMIN_API_KEY` | Used for admin-gated actions (top-up, cancel) |
| `VITE_USER_API_KEY` | User API key if `USER_AUTH_ENABLED=true` |
| `VITE_DEFAULT_PROJECT_ID` | Pre-selects a project on load |

---

## 11. Running Locally

### Backend
```bash
# From repo root
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env — set WAVESPEED_API_KEY and ADMIN_API_KEYS

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Vite proxies `/api` → `http://localhost:8000` (configured in `vite.config.js`).

### RQ worker (optional, only if `QUEUE_BACKEND=rq`)
```bash
python -m backend.app.workers.rq_worker
```

---

## 12. Testing

### Backend tests
```bash
# From repo root
pytest                          # all tests
pytest -m "not live_provider"   # skip tests that call real APIs
pytest backend/tests/test_foo.py -v
```

Tests are in `backend/tests/`. The `live_provider` marker gates any test that calls a real WaveSpeed endpoint. These are opt-in: `pytest -m live_provider`.

### Frontend tests
```bash
cd frontend
npm test                        # runs vitest
```

Test files are colocated: `src/lib/api.test.js`, `src/lib/jobPayloads.test.js`, `src/routes/*.test.jsx`.

---

## 13. Code Style Rules

### Python (backend)
- **Ruff** enforces `E4`, `E7`, `E9`, `F`, `I` rule sets. Run `ruff check .` before committing.
- Line length: **100 characters**.
- Target Python version: **3.10+** (`match` statements, `X | Y` union types are fine).
- Excluded from linting: `backend/generated/`, `.pycaps_repo/`.
- Import order: stdlib → third-party → local (ruff-I enforces this).
- No `from backend.app.xxx import *`.

### JavaScript / JSX (frontend)
- No TypeScript — plain JSX only.
- No Tailwind, no CSS-in-JS. All styles go in `styles.css`.
- No external state management library (no Redux, Zustand, Context for app state).
- Prefer named exports for components.
- Prop names: `onXxx` for callbacks, `xxxLoading` for loading booleans, `xxxResult` for results.
- Do **not** add `style={{}}` inline styles for visual appearance — add a CSS class instead.

### Git
- Commit messages should describe the intent, not the mechanism.
- Never commit `backend/.env` or secrets.
- `backend/generated/` is gitignored — don't track generated files.

---

## 14. Common Patterns & Gotchas

### ⚠️ Idempotency keys are required for job creation
`backend.createJob()` always sends an `Idempotency-Key: <uuid>` header. If you build a raw `fetch` call to the jobs API, include this header or duplicate jobs may be created on retry.

### ⚠️ The sync endpoints and job endpoints share the same payload shape
`POST /api/scripts/generate` (sync) and `POST /api/jobs/scripts/generate` (async) both accept `ScriptRequest`. The payload builders in `lib/jobPayloads.js` return the same objects used in `handleScriptSubmit`.

### ⚠️ `QUEUE_BACKEND=inline` runs jobs synchronously
In development with the default `inline` queue, "Save to Project" still completes synchronously and looks instant. Switch to `rq` to test real async behaviour.

### ⚠️ Auth headers in the frontend
The frontend sends `X-Admin-API-Key` from `VITE_ADMIN_API_KEY`. If this is empty, admin endpoints (top-up, job cancel) will return 401. For local dev, set this to match one of your `ADMIN_API_KEYS`.

### ⚠️ `completedSteps` drives the pipeline sidebar green dots
In `App.jsx`, the `completedSteps` object is derived from result state. If you add a new tab, add its key here too:
```js
const completedSteps = {
  scripts:   Boolean(scriptResult),
  voiceover: Boolean(voiceResult),
  // add new tab here
};
```

### ⚠️ SQLite in-memory vs file mode
`APP_ENV=development` calls `create_tables(engine)` on startup (safe for SQLite). In production, rely on Alembic migrations only. Never call `create_tables` in production code.

### ⚠️ pycaps requires ffmpeg
Caption rendering (`caption_style_generator.py`) uses pycaps which shell-calls `ffmpeg`. Install ffmpeg on the backend host. The Python package is installed from a git commit pin in `requirements.txt`.

### ⚠️ Asset URLs expire
WaveSpeed returns CDN URLs valid for 7 days (`PROVIDER_ASSET_RETENTION_DAYS`). Download assets before they expire. The Dashboard shows an orange "expiring soon" badge in the last 24 hours.

### ⚠️ `resolveQueueConfiguration` returns `null` on missing prerequisites
If the user clicks "Save to Project" without having the required prerequisite data (e.g. trying to queue a voiceover with an empty text field), `resolveQueueConfiguration` returns `null` and `queueProjectJob` sets a user-visible error. Don't bypass this check.

### Adding a new pipeline step (tab)
1. Add it to the `STEPS` array in `GeneratorTabs.jsx` with a new `num` and `id`.
2. Add its state group to `App.jsx` (`xxxForm`, `xxxResult`, etc.).
3. Create `XxxSection.jsx` following the existing pattern (accept `onQueue`, `queueLoading`, `queueMessage`, `queueError` props, render `<ProjectActionCard>`).
4. Add an `{activeTab === "xxx" ? <XxxSection ... /> : null}` block in the pipeline-content div.
5. Add the `xxx: Boolean(xxxResult)` entry to `completedSteps`.
6. Create sync route handler, job route handler, generator module, and registry entry in the backend.

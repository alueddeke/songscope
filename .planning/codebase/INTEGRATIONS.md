# External Integrations

_Last updated: 2026-05-06_

## Summary

SongScope integrates with two external services: the Spotify Web API (for music data, user listening history, and OAuth identity) and the OpenAI API (for GPT-4o-mini-powered feedback interpretation and recommendation explanations). All authentication is delegated entirely to Spotify — there is no separate user registration system. The database is local SQLite. There is no external cache, message queue, file storage service, or monitoring service.

---

## Spotify Web API

**Purpose:** User authentication (OAuth 2.0 identity provider), top tracks/artists, recently played, artist details, recommendations, and adding tracks to user library.

**Client library:** `spotipy==2.23.0` (requirements.txt) / `2.24.0` (installed)

**Additional OAuth library:** `requests-oauthlib==2.0.0` — used directly in `backend/apps/core/views.py` alongside spotipy for the OAuth2 authorization code flow.

**Auth flow:**
1. User hits `GET /spotify-login/` → backend constructs Spotify authorization URL via `OAuth2Session` and redirects the user.
2. Spotify redirects to `GET /spotify/callback/` → backend exchanges the code for tokens using `OAuth2Session.fetch_token()`.
3. Token is stored in the `SpotifyToken` model (Django DB) keyed to the Django `User` object.
4. Subsequent requests use `get_spotipy_client(access_token)` in `backend/apps/spotify/utils.py` to construct an authenticated `spotipy.Spotify` instance.
5. Token refresh is handled manually via `refresh_spotify_token()` in `backend/apps/spotify/utils.py`, which calls `POST https://accounts.spotify.com/api/token` directly with `requests`.

**Scopes requested:**
```
user-read-private user-read-email user-top-read user-read-recently-played
user-library-modify user-read-playback-state user-library-read playlist-read-private
```

**Required env vars (read via `python-decouple` in `backend/config/settings.py`):**
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`

**Env var source:** Loaded from project root `.env` file (confirmed present at `/Users/antonilueddeke/Desktop/Projects/songscope/.env`). Backend reads via `python-decouple`; frontend reads the same root `.env` via `dotenv.config({ path: "../.env" })` in `frontend/next.config.mjs`.

**Rate limiting:** Custom in-process `RateLimitMonitor` class in `backend/apps/spotify/utils.py` tracks requests per second (limit: 25 req/s) and per minute (burst limit: 100 req/min) using a `deque`.

**Spotify CDN images:** `next.config.mjs` whitelists the `i.scdn.co` hostname for Next.js `<Image>` optimisation.

**Relevant files:**
- `backend/apps/core/views.py` — `spotify_login`, `spotify_callback`, all API endpoint handlers
- `backend/apps/spotify/utils.py` — `get_spotipy_client`, `refresh_spotify_token`, `RateLimitMonitor`
- `backend/apps/core/models.py` — `SpotifyToken` model (stores `access_token`, `refresh_token`, `expires_at`)

---

## OpenAI API

**Purpose:** Two distinct uses —
1. **Feedback interpretation** (`FeedbackInterpreter` in `backend/apps/ai/ai_feedback_service.py`): converts free-text user feedback into structured music preference signals (tempo, mood, energy, genre, etc.) via a JSON-returning prompt.
2. **Recommendation explanations** (`RecommendationExplainer` in `backend/apps/ai/ai_feedback_service.py`): generates 1–2 sentence plain-English explanations for why a track was recommended.

**Client library:** `openai==1.99.9`

**Model used:** `gpt-4o-mini` (hardcoded in both `FeedbackInterpreter.interpret_feedback()` and `RecommendationExplainer.generate_explanation()`)

**Token limits:**
- Feedback interpretation: `max_tokens=300`, `temperature=0.1`
- Recommendation explanation: `max_tokens=120`, `temperature=0.7`

**Required env var:**
- `OPENAI_API_KEY` — optional (defaults to `None`); feature degrades gracefully to keyword-based fallback if absent.

**Cost / rate-limit guard:** `RateLimitMonitor` class in `backend/apps/ai/ai_feedback_service.py`:
- Max 50 OpenAI requests per minute (in-process tracking)
- Max $1.00/day cost cap (calculated at $0.15 per 1M tokens for gpt-4o-mini)
- Raises `CostLimitExceeded` exception when daily cap is hit
- Raises `RateLimitExceeded` exception when per-minute limit is hit

**Fallback behaviour:** Both classes check for the client on init; if `OPENAI_API_KEY` is unset or the openai package import fails, they fall back to rule-based keyword matching / static text templates.

**Relevant files:**
- `backend/apps/ai/ai_feedback_service.py` — `FeedbackInterpreter`, `RecommendationExplainer`, `RateLimitMonitor`
- `backend/config/settings.py` — `OPENAI_API_KEY = config('OPENAI_API_KEY', default=None)`

---

## Authentication & Identity

**Provider:** Spotify OAuth 2.0 (authorization code flow) — Spotify IS the identity provider.

**Session management:** Django built-in session framework (`django.contrib.sessions`). After the OAuth callback, the backend creates or retrieves a Django `User` object (keyed on `spotify_id`), then calls `django.contrib.auth.login()` to establish a session cookie.

**Frontend auth:** Session cookie (`sessionid`) + CSRF token (`csrftoken`). The frontend axios client in `frontend/services/axios.ts` reads `csrftoken` from cookies and sends it as the `X-CSRFToken` header on every request. `withCredentials: true` is set so the session cookie is included cross-origin.

**CSRF note:** `CsrfViewMiddleware` is commented out in `backend/config/settings.py` middleware list. CSRF enforcement is applied selectively via the `@ensure_csrf_cookie` decorator and a custom `CsrfExemptSessionAuthentication` class that bypasses enforcement for DRF views.

**DRF authentication:** `SessionAuthentication` with `IsAuthenticated` as the default permission class.

---

## Data Storage

**Database:** SQLite 3
- File: `backend/db.sqlite3`
- ORM: Django ORM
- Engine setting: `django.db.backends.sqlite3`
- No external database (no PostgreSQL, MySQL, etc.)

**Key models** (`backend/apps/core/models.py`):
- `SpotifyToken` — OAuth tokens per user (one-to-one with `User`)
- `UserProfile` — extended profile; stores recommendation cache, feedback history, and preference weights in a `data` JSONField
- `Track` — Spotify track metadata cache
- `UserFeedback` — like/dislike/skip signals per user+track
- `AIFeedback` — stored AI interpretation results per user+track
- `RecommendationLog` — audit log of every recommendation served
- `DailyGem` — one recommended track per user per calendar date (unique on `[user, date]`)

---

## Caching

**No external cache service.** Caching operates at two levels:

1. **In-process dict** (`self._api_cache = {}`) in `HybridRecommendationEngine` (`backend/apps/recommendations/hybrid_recommendation_engine.py`) with a 300-second TTL. This cache does not survive process restarts.

2. **Database-backed** via `UserProfile.data['cache']` JSONField. Methods: `get_from_cache()`, `update_cache()`, `clear_cache()`, `add_to_cache()`. Survives restarts but is per-user and unstructured.

**Note:** The `redis==5.2.0` package is installed in the venv but is **not imported anywhere** in the application code. It may be a leftover dependency.

---

## Frontend → Backend Communication

**Pattern:** REST over HTTP; all requests from the browser to `http://localhost:8000` (or whatever `NEXT_PUBLIC_BACKEND_URL` resolves to).

**HTTP client:** `axios ^1.7.7` — wrapped in `frontend/services/axios.ts`

**Base URL env var:**
- `NEXT_PUBLIC_BACKEND_URL` — read in `frontend/services/axios.ts`, falls back to `http://localhost:8000`

**CORS:** Configured in `backend/config/settings.py`:
- Allowed origins: `http://localhost:3000`, `http://127.0.0.1:3000`
- `CORS_ALLOW_CREDENTIALS = True`
- `corsheaders.middleware.CorsMiddleware` is first in the middleware stack

---

## File Storage

- No external file storage (no S3, GCS, Cloudinary, etc.)
- Track album artwork is referenced as Spotify CDN URLs (`i.scdn.co`) stored as `URLField` on `DailyGem.image_url`
- Static files served by Django staticfiles at `static/`

---

## Monitoring & Observability

- No external error tracking service (no Sentry, Datadog, Rollbar, etc.)
- Django's built-in logging framework is used throughout (`logging.getLogger(__name__)`)
- A logging config block exists in `backend/config/settings.py` but is **commented out** — no active logging handlers configured at the settings level
- Debug log file: `backend/debug.log` (present in repo)

---

## CI/CD & Deployment

- No CI configuration found (no `.github/workflows/`, no `Jenkinsfile`, no `Makefile`)
- No Dockerfile or docker-compose file present
- No deployment platform configuration detected (no `Procfile`, `app.yaml`, `render.yaml`, etc.)
- Project appears to be development-only at this stage

---

## Environment Variables Reference

All backend env vars are read via `python-decouple`'s `config()` in `backend/config/settings.py`.

| Variable | Required | Used By | Notes |
|----------|----------|---------|-------|
| `SPOTIFY_CLIENT_ID` | Yes | Backend settings, `views.py` | No default |
| `SPOTIFY_CLIENT_SECRET` | Yes | Backend settings, `views.py` | No default |
| `SPOTIFY_REDIRECT_URI` | Yes | Backend settings, `views.py` | No default |
| `OPENAI_API_KEY` | No | `ai_feedback_service.py` | Defaults to `None`; AI features degrade gracefully |
| `FRONTEND_URL` | Yes | Backend settings | No default; used for CORS/redirect logic |
| `OAUTHLIB_INSECURE_TRANSPORT` | No | Backend settings | Set to `'1'` in `views.py` before imports |
| `NEXT_PUBLIC_BACKEND_URL` | No | `frontend/services/axios.ts` | Defaults to `http://localhost:8000` |

**Env file locations:**
- Project root: `/Users/antonilueddeke/Desktop/Projects/songscope/.env` (shared; read by both backend via decouple and frontend via dotenv in `next.config.mjs`)
- Frontend local override: `frontend/.env.local` (loaded second in `next.config.mjs`)

---

## Key Observations

- Spotify is the **sole identity provider** — there is no email/password registration. All user accounts map 1:1 to a Spotify user ID.
- OpenAI integration is **optional** — the app functions without `OPENAI_API_KEY` using keyword-based fallbacks.
- The **redis package is installed but unused** — likely installed as a future intention; should be removed from the venv or added to requirements if needed.
- **CSRF middleware is disabled globally** and bypassed in DRF via a custom authentication class — this is a known dev shortcut documented in the code.
- The shared root `.env` is read by `next.config.mjs` and injects `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` into the Next.js build environment — these values become visible in the compiled client bundle.
- No webhooks are registered with Spotify or OpenAI; all integration is request/response polling.
- SQLite is the only database. There is no migration to a production-grade database planned or configured.

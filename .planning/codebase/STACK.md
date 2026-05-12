# Technology Stack

_Last updated: 2026-05-06_

## Summary

SongScope is a fullstack music discovery application with a Python/Django REST API backend and a Next.js/TypeScript frontend. The backend handles Spotify OAuth, AI-powered recommendation logic, and all data persistence. The frontend is a React single-page app consuming the backend REST API over HTTP with session-based auth. The two halves are developed in separate directories (`backend/` and `frontend/`) with no shared build tooling.

---

## Languages

**Backend:**
- Python 3.11.7 — entire backend (`backend/`)
- No `.python-version` pin file present; version inferred from `backend/venv/lib/python3.11/`

**Frontend:**
- TypeScript 5.x — all frontend source (`frontend/app/`, `frontend/services/`)
- JavaScript (ESM) — `frontend/next.config.mjs`, `frontend/postcss.config.mjs`

---

## Runtimes

| Layer | Runtime | Version |
|-------|---------|---------|
| Backend | CPython | 3.11.7 |
| Frontend | Node.js | 21.7.1 |

---

## Package Managers

**Backend:**
- pip — primary installer
- `backend/requirements.txt` — pinned dependency list
- `backend/Pipfile.lock` — present (Pipenv lockfile), though `Pipfile` itself is absent
- Two virtual environments present: `backend/venv/` (active) and `backend/env/` (stale)

**Frontend:**
- npm 10.5.0 — `frontend/package-lock.json` present
- No `yarn.lock` or `pnpm-lock.yaml`

---

## Frameworks

### Backend

| Framework | Version (requirements.txt) | Installed Version | Purpose |
|-----------|---------------------------|-------------------|---------|
| Django | 5.1.3 | 5.1.3 | Web framework, ORM, session auth |
| Django REST Framework | 3.15.2 | 3.15.1 | REST API, serializers, pagination |
| django-cors-headers | 4.3.1 | 4.6.0 | CORS middleware |

### Frontend

| Framework | Version (package.json) | Purpose |
|-----------|------------------------|---------|
| Next.js | 14.2.4 | React meta-framework, App Router |
| React | ^18 | UI rendering |
| React DOM | ^18 | DOM bindings |

---

## Key Dependencies

### Backend (`backend/requirements.txt` + installed venv)

| Package | Version | Purpose |
|---------|---------|---------|
| spotipy | 2.23.0 req / 2.24.0 installed | Spotify Web API client |
| requests | 2.31.0 req / 2.32.3 installed | HTTP client for token refresh |
| requests-oauthlib | 2.0.0 | Spotify OAuth2 flow (`OAuth2Session`) |
| oauthlib | 3.2.2 | OAuth2 primitives used by requests-oauthlib |
| openai | 1.99.9 | GPT-4o-mini for feedback interpretation and recommendation explanations |
| python-decouple | 3.8 | Env var loading via `config()` in `settings.py` |
| numpy | 2.1.3 installed | Vector math for recommendation scoring in `hybrid_recommendation_engine.py` |
| pydantic | 2.11.7 | Used by openai SDK internally |
| redis | 5.2.0 installed | Package present in venv but NOT actively imported in application code — caching is in-process (dict + Django JSONField) |
| asgiref | 3.8.1 | Async support for Django |
| sqlparse | 0.5.1 | Django ORM SQL formatting |
| python-dotenv | 1.1.1 | Also installed (alongside python-decouple) |

### Frontend (`frontend/package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| axios | ^1.7.7 | HTTP client — all API calls via `frontend/services/axios.ts` |
| next | 14.2.4 | Framework |
| react | ^18 | UI |
| lucide-react | ^0.454.0 | Icon library |
| react-h5-audio-player | ^3.9.3 | Audio preview playback |
| react-switch | ^7.0.0 | Toggle switch component |
| sass | ^1.80.5 | SCSS support |
| shadcn-ui | ^0.9.2 | Component library (also `@shadcn/ui ^0.0.4` — duplicate entries) |
| dotenv | ^16.4.5 | Loaded in `next.config.mjs` to read shared `.env` from project root |
| tailwindcss | ^3.4.1 | Utility CSS |
| postcss | ^8 | CSS processing |
| typescript | ^5 | Type checking |
| eslint | ^8 | Linting |
| eslint-config-next | 14.2.4 | Next.js ESLint rules |

---

## Build & Dev Tooling

### Backend
- `python manage.py runserver` — development server (WSGI, not ASGI)
- No dedicated build step; Django serves via WSGI at `config/wsgi.py`
- No containerisation config found (no `Dockerfile`, no `docker-compose.yml`)

### Frontend
| Command | Purpose |
|---------|---------|
| `npm run dev` | Next.js dev server (`next dev`) |
| `npm run build` | Production build (`next build`) |
| `npm run start` | Production server (`next start`) |
| `npm run lint` | ESLint (`next lint`) |

---

## Database

- **Engine:** SQLite 3
- **File:** `backend/db.sqlite3` (committed to repo)
- **ORM:** Django ORM (Django models)
- Config in `backend/config/settings.py`:
  ```python
  DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
  ```

---

## TypeScript Configuration

- **Strict mode:** enabled (`"strict": true`)
- **Module resolution:** `"bundler"` (Next.js optimised)
- **Path alias:** `@/*` maps to `./` (repo-relative from `frontend/`)
- Config: `frontend/tsconfig.json`

---

## CSS / Styling

- Tailwind CSS 3.4.1 — utility classes, config at `frontend/tailwind.config.ts`
- Custom color palette defined: `dark`, `navy`, `orange`, `light-gray`, `white`, `brown`, `green` (Spotify green `#1DB954`)
- Sass 1.80.5 — for any SCSS files in `frontend/styles/`
- PostCSS — config at `frontend/postcss.config.mjs`

---

## Security Configuration (Development)

- `DEBUG = True` in `backend/config/settings.py`
- CSRF middleware is **commented out**: `# "django.middleware.csrf.CsrfViewMiddleware"`
- `CSRF_COOKIE_SECURE = False`
- `SESSION_COOKIE_SECURE = False`
- Django `SECRET_KEY` is hardcoded as an insecure placeholder string
- `OAUTHLIB_INSECURE_TRANSPORT = '1'` is force-set in `backend/apps/core/views.py` to allow HTTP OAuth redirects locally

---

## Key Observations

- Requirements.txt pins `spotipy==2.23.0` but `2.24.0` is actually installed — version drift.
- `redis` package is installed in the venv but is **not imported** anywhere in application code; caching is purely in-memory (dict inside `HybridRecommendationEngine`) and in the database (`UserProfile.data` JSONField).
- Two shadcn package entries exist in `package.json` (`@shadcn/ui ^0.0.4` and `shadcn-ui ^0.9.2`) — likely a duplicate/legacy entry.
- No `.nvmrc` or `.python-version` file; Node and Python versions are not pinned at the project level.
- `python-dotenv` and `python-decouple` are both installed; only `python-decouple` is used in `settings.py`.
- The frontend reads a shared `.env` from the project root via `dotenv.config({ path: "../.env" })` in `next.config.mjs`, exposing Spotify credentials to the Next.js build.
- No testing framework is listed in `requirements.txt` or `package.json`; `backend/tests/` directory exists but has no declared test runner.

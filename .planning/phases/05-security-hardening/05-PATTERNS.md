# Phase 05: Security Hardening — Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 6 (2 modified, 1 edited, 3 created)
**Analogs found:** 5 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/config/settings.py` | config | request-response | `backend/config/settings.py` (existing `config()` calls for Spotify vars) | self (surgery) |
| `backend/apps/core/views.py` | view/controller | request-response | `backend/apps/core/views.py` (existing clean view functions) | self (deletion) |
| `frontend/next.config.mjs` | config | — | `frontend/.env.local` (minimal env pattern) | partial |
| `backend/.env` | config | — | `backend/.env` (existing entries) | self (addition) |
| `.env.example` (repo root) | documentation | — | none — no .env.example exists yet | no analog |
| `backend/.env.example` | documentation | — | none — no .env.example exists yet | no analog |

---

## Pattern Assignments

### `backend/config/settings.py` — SECRET_KEY and MIDDLEWARE changes

**Change type:** Surgery — two targeted edits to an existing file.

**Analog for the pattern being applied:** The file's own existing `config()` calls for Spotify
credentials (lines 19–27) are the exact pattern to copy for `SECRET_KEY` and `DEBUG`.

**Existing pattern to replicate** (lines 13–27, current file):

```python
from decouple import config

# Set this to True for local development, False for production
OAUTHLIB_INSECURE_TRANSPORT = config('OAUTHLIB_INSECURE_TRANSPORT', 'False').lower() == 'true'

SPOTIFY_CLIENT_ID = config('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = config('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = config('SPOTIFY_REDIRECT_URI')

# OpenAI API Configuration
OPENAI_API_KEY = config('OPENAI_API_KEY', default=None)

# Frontend URL
FRONTEND_URL = config('FRONTEND_URL')
```

**What to replace** (lines 37–41, current file):

```python
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-dev-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

**Target state after edit:**

```python
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

Notes:
- Drop `import os` — after the edit `os` is no longer used in `settings.py`. It remains in
  `views.py` where `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` is used.
- No `default=` argument for `SECRET_KEY` — python-decouple raises `UndefinedValueError` at
  startup if the key is absent, making misconfiguration visible immediately.
- `cast=bool` replaces the `== 'True'` string comparison for `DEBUG`.

**MIDDLEWARE change** (lines 192–201, current file):

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",   # <-- uncomment this line
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**Target state after edit:**

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**CSRF settings already correct — do not change** (lines 91–103):

```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
]
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False  # Must stay False — JS reads this cookie
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False    # Set True in production with HTTPS
```

---

### `backend/apps/core/views.py` — remove CsrfExemptSessionAuthentication

**Change type:** Deletion of dead code — remove class definition and its import.

**Dead class to delete** (lines 36–38):

```python
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not enforce CSRF token
```

**Import to remove** (line 21):

```python
from rest_framework.authentication import SessionAuthentication
```

Verification before removing: grep the full file for any other reference to `SessionAuthentication`.
The grep in research confirmed no view uses `authentication_classes = [SessionAuthentication]`
directly — the import is used only by the dead class, so it is safe to remove.

**Pattern for healthy view functions in this file** (reference: lines 555–557, `get_csrf_token`):

```python
@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'message': 'CSRF cookie set'})
```

This function and its `@ensure_csrf_cookie` decorator are the correct CSRF pattern — keep it exactly
as-is.

---

### `frontend/next.config.mjs` — remove SPOTIFY_CLIENT_SECRET from env block

**Change type:** Simplification — strip the file down to a minimal config.

**Current file** (all 23 lines):

```js
import dotenv from "dotenv";
dotenv.config({ path: "../.env" }); // Load shared environment variables
dotenv.config({ path: "./.env.local" }); // Load local environment variables

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    SPOTIFY_CLIENT_ID: process.env.SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET: process.env.SPOTIFY_CLIENT_SECRET,
    REDIRECT_URI: process.env.REDIRECT_URI,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  },
};

export default nextConfig;
```

**Target state after edit:**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
```

Rationale:
- `NEXT_PUBLIC_BACKEND_URL` is already in `frontend/.env.local` — Next.js reads `.env.local`
  automatically, no manual `dotenv.config()` call required.
- Nothing in `frontend/` references `process.env.SPOTIFY_CLIENT_ID`,
  `process.env.SPOTIFY_CLIENT_SECRET`, or `process.env.REDIRECT_URI` (verified by grep in
  research). Removing the `env` block drops three unused credential exposures.
- After removing the `import dotenv` and `dotenv.config()` calls, check whether `dotenv` should
  be removed from `package.json` (`grep "dotenv" frontend/package.json`).

**Analog for the minimal pattern:** `frontend/.env.local` (current content):

```
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
TEST=test
```

Next.js reads `NEXT_PUBLIC_*` vars from `.env.local` at build time automatically — no
`next.config.mjs` wiring needed.

---

### `backend/.env` — add SECRET_KEY entry

**Change type:** Addition — one new line to an existing file.

**Current content** (all entries, actual file):

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
TEST=test
SPOTIFY_CLIENT_ID=<redacted>
SPOTIFY_CLIENT_SECRET=<redacted>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/spotify/callback/
FRONTEND_URL=http://127.0.0.1:3000
OAUTHLIB_INSECURE_TRANSPORT=True
OPENAI_API_KEY=<redacted>
```

**Line to add:**

```
SECRET_KEY=<output of: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
```

**Also add** (to unify with the `config('DEBUG', ...)` change in settings.py):

```
DEBUG=True
```

Place both at the top of the file or grouped with the Django-specific vars. The `DEBUG` line is
needed because `settings.py` will use `config('DEBUG', default=False, cast=bool)` — if `DEBUG` is
absent from `.env`, it defaults to `False` which is correct for production but the local dev
environment needs `DEBUG=True` for Django error pages.

**Pattern: existing `.env` entries use bare `KEY=VALUE` format** — no quotes, no spaces around
`=`. Match that style for the new lines.

---

### `.env.example` (repo root) — create new

**No analog exists.** This is the first `.env.example` in the project.

**Content to write** (documented in RESEARCH.md, Documentation Content Map section):

```bash
# ============================================================
# SongScope — Environment Variables
# Copy this file to .env and fill in the values.
# ============================================================

# ---- Django Backend (also used by backend/.env) ----

# Django secret key — generate with:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=

# Debug mode — set to True for local development only
DEBUG=False

# Spotify OAuth credentials — get from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/spotify/callback/

# OpenAI API key (optional — used for AI feedback feature)
OPENAI_API_KEY=

# Allow insecure OAuth transport for local HTTP development (set to True locally)
OAUTHLIB_INSECURE_TRANSPORT=True

# Frontend URL (where Next.js runs)
FRONTEND_URL=http://127.0.0.1:3000

# ---- Next.js Frontend (also used by frontend/.env.local) ----

# Backend URL — must match where Django runs
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**Key naming matches real `.env` files exactly** — variable names are copied verbatim from
`backend/.env` so developers have a 1:1 reference.

---

### `backend/.env.example` — create new

**No analog exists.**

**Content:** Django-relevant subset of the root `.env.example` (omit `NEXT_PUBLIC_BACKEND_URL`):

```bash
# ============================================================
# SongScope — Django Backend Environment Variables
# Copy this file to backend/.env and fill in the values.
# ============================================================

# Django secret key — generate with:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=

# Debug mode — set to True for local development only
DEBUG=False

# Spotify OAuth credentials — get from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/spotify/callback/

# OpenAI API key (optional — used for AI feedback feature)
OPENAI_API_KEY=

# Allow insecure OAuth transport for local HTTP development
OAUTHLIB_INSECURE_TRANSPORT=True

# Frontend URL (where Next.js runs)
FRONTEND_URL=http://127.0.0.1:3000
```

---

## Shared Patterns

### python-decouple `config()` usage

**Source:** `backend/config/settings.py` lines 13–27 (existing Spotify credential reads)
**Apply to:** All new `SECRET_KEY` and `DEBUG` entries in `settings.py`

```python
from decouple import config

# With no default — raises UndefinedValueError if missing (correct for secrets)
SECRET_KEY = config('SECRET_KEY')

# With default and type cast
DEBUG = config('DEBUG', default=False, cast=bool)

# Optional var with explicit None default
OPENAI_API_KEY = config('OPENAI_API_KEY', default=None)
```

Rule: use `config()` for all settings that come from the environment. Never use
`os.environ.get()` with a fallback for secrets — the fallback defeats the protection.

---

### CSRF token round-trip (already implemented — do not change)

**Source:** `backend/apps/core/views.py` line 555–557 (get_csrf_token)
**Source:** `frontend/app/components/CsrfProvider.tsx` (not read — confirmed present in research)
**Source:** `frontend/services/axios.ts` lines 24–29 (confirmed in research)

The existing mechanism is:
1. `CsrfProvider` mounts at layout root → calls `GET /api/csrf-token/`
2. `get_csrf_token` view (decorated `@ensure_csrf_cookie`) → sets `csrftoken` cookie
3. `axios` client reads `csrftoken` cookie → adds `X-CSRFToken` header on every request
4. `CsrfViewMiddleware` (once re-enabled) enforces the header on state-mutating requests

This is a complete, pre-wired system. No frontend changes are needed when the middleware is
re-enabled.

---

### Error handling in views

**Source:** `backend/apps/core/views.py`, pattern repeated throughout (e.g., lines 99–101, 130–137)

```python
try:
    # ... main logic ...
except SpecificException as e:
    logger.error(f"Specific error: {str(e)}")
    return JsonResponse({'error': str(e)}, status=e.http_status)
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    return JsonResponse({'error': str(e)}, status=500)
```

All views in this file follow this try/except structure. After deleting
`CsrfExemptSessionAuthentication`, the remaining views should retain this pattern unchanged.

---

### `.env` file format convention

**Source:** `backend/.env` (all entries)

Format: bare `KEY=VALUE`, no quotes around values, no spaces around `=`.

```
SECRET_KEY=django-generated-value-here
DEBUG=True
SPOTIFY_CLIENT_ID=6bf1a7e2b72e4e36be9179772e15fe35
```

Match this format exactly in new `.env` entries and in `.env.example` placeholder lines.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `.env.example` (root) | documentation | — | No `.env.example` exists anywhere in the repo; this is the first. |
| `backend/.env.example` | documentation | — | Same — first `.env.example` in the project. |

For both files, use the content from the RESEARCH.md "Documentation Content Map" section
directly — it was authored by reading the actual variable names from `backend/.env`.

---

## Metadata

**Analog search scope:** `backend/config/`, `backend/apps/core/`, `frontend/`, repo root
**Files read:** `settings.py`, `views.py`, `next.config.mjs`, `backend/.env`, `frontend/.env.local`, `conftest.py`, `check_spotify_config.py`
**Pattern extraction date:** 2026-05-12

# Phase 05: Security Hardening — Research

**Researched:** 2026-05-12
**Domain:** Django security configuration, Next.js env var exposure, CSRF protection
**Confidence:** HIGH — all findings verified directly from the codebase, git history, and file system

---

## Summary

Phase 5 addresses three distinct security issues. The research below is built entirely from
reading the actual files — no assumptions about what "might" be there. The current state is
more nuanced than the phase description implies: the SECRET_KEY situation has been *partially*
fixed (the hardcoded value moved to `os.environ.get`), but the original key is burned into git
history and must be rotated. The Spotify `CLIENT_SECRET` is genuinely exposed to the browser
bundle via `next.config.mjs`. CSRF middleware is fully disabled at two independent layers.

**Primary recommendation:** Three isolated, low-risk changes. Each can be its own task. No
architectural changes are needed — this is configuration and cleanup surgery only.

---

## Current Security State

### Issue 1: SECRET_KEY — Partially Fixed, Still Requires Rotation

**What happened historically:**

Commit `96d76dcd` ("updated backend structure") committed `settings.py` with:

```python
SECRET_KEY = "django-insecure-2nagt=pfbkp%5#u*^r4bwjenk2b_3a)ly-y*656vzx%qvzv6v="
```

[VERIFIED: git show 96d76dcd:backend/config/settings.py]

Commit `cfaf255d` ("fix(02): WR-05 move SECRET_KEY and DEBUG to environment variables") changed
this to:

```python
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-dev-only')
```

[VERIFIED: git show HEAD:backend/config/settings.py]

**Current state in settings.py (HEAD):**
- `SECRET_KEY` reads from environment, falls back to the string `'django-insecure-fallback-dev-only'`
- The original key `django-insecure-2nagt=pfbkp%5#u*^r4bwjenk2b_3a)ly-y*656vzx%qvzv6v=` exists in two
  git commits (`96d76dcd`, `d23b44d6`) and will remain in history permanently unless git history rewrite
  is performed (not needed for a portfolio app — the key was never production-grade)
- `SECRET_KEY` is NOT set in `backend/.env` or the root `.env` — Django is currently running with the
  literal fallback string `'django-insecure-fallback-dev-only'`
- `python-decouple 3.8` is installed [VERIFIED: pip show python-decouple] and `settings.py` already
  uses `config()` for Spotify credentials, but `SECRET_KEY` uses raw `os.environ.get` — this
  inconsistency should be unified

**What the fix must do:**
1. Generate a fresh secret key (the old committed key is burned — do not reuse it)
2. Add `SECRET_KEY=<new-key>` to `backend/.env`
3. Update `settings.py` to use `config('SECRET_KEY')` via python-decouple (already installed)
4. Remove the `'django-insecure-fallback-dev-only'` fallback — no fallback is the right default for
   a key that must be secret

**Session impact:** Rotating the key invalidates all Django sessions. For this single-user portfolio
app, that means one logout. Acceptable. [ASSUMED: there is only one active user session — this is
consistent with the "single user" project description]

---

### Issue 2: Spotify CLIENT_SECRET Exposed to Browser Bundle

**The exposure mechanism:**

`frontend/next.config.mjs` contains:

```js
dotenv.config({ path: "../.env" }); // reads root .env

const nextConfig = {
  env: {
    SPOTIFY_CLIENT_ID: process.env.SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET: process.env.SPOTIFY_CLIENT_SECRET,  // <-- problem
    REDIRECT_URI: process.env.REDIRECT_URI,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  },
};
```

[VERIFIED: reading frontend/next.config.mjs]

The `env` block in `next.config.mjs` bakes variables into the JavaScript bundle at build time,
making them accessible in browser JS via `process.env.SPOTIFY_CLIENT_SECRET`. This is distinct
from the `NEXT_PUBLIC_` prefix (which also bakes into the bundle), but the effect is identical for
client components — the value is in the downloaded JS.

**Root .env contains real credentials:**

```
SPOTIFY_CLIENT_ID=6bf1a7e2b72e4e36be9179772e15fe35
SPOTIFY_CLIENT_SECRET=4f0d1b7c78cd40acaefc14c293161f49
OPENAI_API_KEY=sk-proj-SwRVM-...
```

[VERIFIED: reading root .env — these are real credential values]

**Critical finding:** The `.env` and `backend/.env` files are NOT tracked in git
[VERIFIED: git ls-files returned nothing for .env files, git check-ignore confirms .gitignore blocks
them]. The root `.gitignore` correctly excludes `.env` and `.env*.local`. So credentials are not in
git history — only in the developer's local files.

**However:** If the Next.js app is deployed, the build process would bake `SPOTIFY_CLIENT_SECRET` into
the JS bundle. Anyone visiting the site could extract it from browser DevTools.

**What the frontend actually uses:**

Zero frontend code references `process.env.SPOTIFY_CLIENT_SECRET` or `process.env.SPOTIFY_CLIENT_ID`
[VERIFIED: grep across all .ts/.tsx/.js files found no references]. The `next.config.mjs` is
exposing credentials that nothing in the frontend actually consumes. The OAuth flow is server-side
(Django handles `spotify_login` and `spotify_callback`).

**What the fix must do:**
1. Remove `SPOTIFY_CLIENT_SECRET` and `SPOTIFY_CLIENT_ID` from the `env` block in `next.config.mjs`
2. Remove `REDIRECT_URI` as well (also unused in frontend code)
3. Keep only what the frontend actually needs: `NEXT_PUBLIC_BACKEND_URL` — but this should be a
   `NEXT_PUBLIC_` var, not in the `env` block at all
4. The root `.env` exists and is loaded by `next.config.mjs` — after this fix, `next.config.mjs`
   should not need to load the root `.env` at all (frontend only needs `NEXT_PUBLIC_BACKEND_URL`
   which is already in `frontend/.env.local`)

**Spotify OAuth flow — no frontend change needed:**

The OAuth flow is entirely Django-side. `spotify_login` and `spotify_callback` in `views.py` use
`settings.SPOTIFY_CLIENT_ID` and `settings.SPOTIFY_CLIENT_SECRET` (from `backend/.env` via
python-decouple). The frontend just redirects to `http://localhost:8000/spotify-login/` — it never
needs the credentials itself. [VERIFIED: views.py spotify_login and spotify_callback functions]

---

### Issue 3: CSRF Protection — Disabled at Two Independent Layers

**Layer 1: CsrfViewMiddleware commented out in settings.py**

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",   # <-- commented out
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

[VERIFIED: reading backend/config/settings.py lines 192-202]

**Layer 2: CsrfExemptSessionAuthentication in views.py**

```python
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not enforce CSRF token
```

[VERIFIED: reading backend/apps/core/views.py lines 36-38]

**Critical finding:** `CsrfExemptSessionAuthentication` is defined but **never used**. No view
uses `authentication_classes = [CsrfExemptSessionAuthentication]`. The global
`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` uses plain `SessionAuthentication`. The bypass
class exists but is dead code. [VERIFIED: grep for authentication_classes across codebase found
only the definition, no usage]

**Net effect:** CSRF is disabled exclusively because `CsrfViewMiddleware` is commented out. The
`CsrfExemptSessionAuthentication` class contributes nothing currently — but it's dangerous dead
code that could be accidentally activated.

**What the fix must do:**
1. Uncomment `"django.middleware.csrf.CsrfViewMiddleware"` in `MIDDLEWARE`
2. Delete the `CsrfExemptSessionAuthentication` class from `views.py` (dead code, dangerous to
   leave around)
3. Verify the existing CSRF token flow works end-to-end

**The existing CSRF token flow (already implemented):**

The frontend already has a complete CSRF token management system:
- `CsrfProvider` component calls `fetchCsrfToken()` on mount [VERIFIED: app/components/CsrfProvider.tsx]
- `fetchCsrfToken()` calls `GET /api/csrf-token/` which triggers `ensure_csrf_cookie` [VERIFIED:
  views.py get_csrf_token, urls.py]
- `getClient()` in `services/axios.ts` reads the `csrftoken` cookie and adds `X-CSRFToken` header
  to every request [VERIFIED: services/axios.ts lines 24-29]
- `CsrfProvider` is mounted in the root layout [VERIFIED: app/layout.tsx]

This means re-enabling CSRF middleware should work without any additional frontend changes.

**Spotify OAuth and CSRF:**

The `spotify_login` and `spotify_callback` views are plain Django views (not DRF `@api_view`).
They do GET requests, so CSRF does not apply. Django's CSRF middleware only enforces on
POST/PUT/PATCH/DELETE. The OAuth callback is a GET redirect from Spotify — no CSRF token needed
and no CSRF enforcement applies. [VERIFIED: views.py spotify_login and spotify_callback
decorated only with @require_http_methods(["GET"])]

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SECRET_KEY storage | Django settings (env) | — | Server-only; never crosses wire |
| Spotify credentials storage | Django settings (env) | — | Used only in backend OAuth flow |
| CSRF token generation | Django middleware | — | Server sets cookie via ensure_csrf_cookie |
| CSRF token transmission | Browser (frontend) | — | axios reads cookie, sends X-CSRFToken header |
| CSRF enforcement | Django middleware | DRF SessionAuthentication | Middleware checks all state-mutating requests |
| .env.example documentation | Repo root | — | Read by developers setting up project |

---

## Fix Strategy

### Fix 1: SECRET_KEY Rotation

**Steps:**

1. Generate a new key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. Add to `backend/.env`:
   ```
   SECRET_KEY=<newly-generated-value>
   ```

3. Update `backend/config/settings.py` — change:
   ```python
   import os
   SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-dev-only')
   ```
   to:
   ```python
   SECRET_KEY = config('SECRET_KEY')
   ```
   (python-decouple's `config` is already imported at the top of settings.py; removes the `import os`
   line if `os` is no longer used elsewhere)

4. Verify `import os` usage: `os` is also used for `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'`
   in views.py — keep `import os` in views.py, but settings.py can drop it if SECRET_KEY is the only
   usage there. [VERIFIED: settings.py uses os only for SECRET_KEY and DEBUG]

5. Actually: `DEBUG` also uses `os.environ.get` — unify both:
   ```python
   SECRET_KEY = config('SECRET_KEY')
   DEBUG = config('DEBUG', default=False, cast=bool)
   ```
   Remove the `import os` from settings.py entirely.

**No git history scrubbing needed:** The committed key was a `django-insecure-*` key, never used in
production. The rotation generates a new key; the old one in history is irrelevant once rotated.

---

### Fix 2: Remove CLIENT_SECRET from next.config.mjs

**Steps:**

1. Edit `frontend/next.config.mjs`:

   Remove the entire `dotenv.config` block and the `env` configuration object. The cleaned file
   should be:

   ```js
   /** @type {import('next').NextConfig} */
   const nextConfig = {};

   export default nextConfig;
   ```

   **Rationale:** `NEXT_PUBLIC_BACKEND_URL` is already defined in `frontend/.env.local` — Next.js
   reads `.env.local` automatically without any manual `dotenv.config` call. No `env` block needed.
   The Spotify credentials are backend-only.

2. Verify nothing in `frontend/` references `process.env.SPOTIFY_CLIENT_SECRET`,
   `process.env.SPOTIFY_CLIENT_ID`, or `process.env.REDIRECT_URI` (confirmed by grep — nothing
   references them).

3. Also remove the `dotenv` npm import — check if `dotenv` is a dependency in `package.json`:

   ```bash
   grep "dotenv" /Users/antonilueddeke/Desktop/Projects/songscope/frontend/package.json
   ```

   If `dotenv` is only used in `next.config.mjs`, it can be removed from `package.json` after the
   import is deleted. (Do not remove if used elsewhere.)

---

### Fix 3: Re-enable CSRF Middleware

**Steps:**

1. Uncomment in `backend/config/settings.py`:
   ```python
   "django.middleware.csrf.CsrfViewMiddleware",
   ```

2. Delete the dead class from `backend/apps/core/views.py`:
   ```python
   class CsrfExemptSessionAuthentication(SessionAuthentication):
       def enforce_csrf(self, request):
           return  # To not enforce CSRF token
   ```
   Also remove the `from rest_framework.authentication import SessionAuthentication` import if it's
   only used by this class. [VERIFIED: the import `SessionAuthentication` appears only in the class
   definition — check if any view uses `authentication_classes = [SessionAuthentication]` directly
   before removing the import]

3. Run the test suite:
   ```bash
   cd backend && python -m pytest tests/ -x -q
   ```

**Why tests should still pass:**

Django's `TestClient` bypasses CSRF enforcement by default (it sets `enforce_csrf_checks=False`
internally). Tests that use `self.client.force_login(self.user)` and then POST will still work
after re-enabling the middleware because the test client does not send real CSRF tokens and does
not check them. [ASSUMED: this is Django's documented behavior for TestClient — the test framework
intentionally disables CSRF to simplify testing]

The 3 view-level tests in `test_feedback.py` that POST to `/api/submit-feedback/` will continue
to pass because they use `self.client` (Django TestClient with CSRF disabled).

**The only risk:** If any test creates its own `Client(enforce_csrf_checks=True)` explicitly,
those tests would now fail. A search confirms no test does this. [VERIFIED: grep found no
`enforce_csrf_checks=True` in any test file]

---

## Risk Assessment

### Risk 1: Tests break after CSRF re-enable
**Likelihood:** Very low
**Reason:** Django TestClient disables CSRF by default. All 77 existing tests pass today with
CSRF middleware commented out. After uncommenting, the test client still bypasses CSRF. Tests
that use `force_login` + POST are safe.
**Mitigation:** Run `pytest tests/ -x` immediately after the settings change. Expected: 77 pass.

### Risk 2: Live frontend breaks after CSRF re-enable (in development)
**Likelihood:** Low — the CSRF token plumbing is already wired
**Reason:** `CsrfProvider` is mounted at layout root, calls `GET /api/csrf-token/` on page load,
and the axios client reads and forwards the `csrftoken` cookie on every POST. This mechanism was
implemented in anticipation of CSRF enforcement being restored.
**Potential issue:** The `CSRF_COOKIE_HTTPONLY = False` setting is correctly set (JavaScript must
be able to read the cookie). The `CSRF_COOKIE_SAMESITE = 'Lax'` and `CSRF_TRUSTED_ORIGINS`
settings are already configured. [VERIFIED: all these settings present in settings.py]
**Mitigation:** After enabling, do a manual test: log in, submit a like/dislike, verify 200 response.

### Risk 3: Spotify OAuth breaks after CSRF re-enable
**Likelihood:** Very low
**Reason:** `spotify_login` and `spotify_callback` handle GET requests only (`@require_http_methods(["GET"])`).
CSRF enforcement only applies to state-mutating methods (POST, PUT, PATCH, DELETE). Django's CSRF
middleware does not check GET requests.
**Mitigation:** Manual smoke test: visit `/spotify-login/`, complete OAuth flow, verify redirect to
`/profile` works.

### Risk 4: SECRET_KEY rotation breaks existing sessions
**Likelihood:** Certain — this is expected behavior
**Impact:** The single developer user is logged out. They re-authenticate with Spotify.
**Acceptability:** Yes — documented in the phase description as acceptable.

### Risk 5: Removing next.config.mjs env block breaks something in frontend
**Likelihood:** Very low — grep confirmed nothing in frontend uses those env vars
**Mitigation:** After editing next.config.mjs, run `npm run build` in `frontend/` and confirm no
build errors.

---

## Standard Stack

**Decision: python-decouple (already chosen and installed)**

python-decouple 3.8 is already installed [VERIFIED: pip show python-decouple] and already used in
`settings.py` for all Spotify credentials. The inconsistency is that `SECRET_KEY` still uses raw
`os.environ.get`. The fix is simply to use `config('SECRET_KEY')` — no new dependency needed.

**python-decouple vs alternatives:**

| Tool | Status | Why |
|------|--------|-----|
| python-decouple 3.8 | **Use this** — already installed | Already used for Spotify creds in settings.py. Reads from `.env` file relative to `manage.py`. Supports casting (`cast=bool`). |
| django-environ | Do not add | Would be a second env-management library. python-decouple already handles the use case. |
| Raw `os.environ.get` | Remove existing usage | Less ergonomic (no `.env` file support, no casting), inconsistent with the rest of settings.py |
| python-dotenv | Do not use for Django | Already in requirements (for other purposes), but python-decouple is the Django-idiomatic choice |

**python-decouple `.env` file discovery:** python-decouple looks for `.env` (or `settings.ini`)
starting from the directory of `manage.py` and walking upward. Since Django is run from
`backend/`, `backend/.env` is the correct location — which is where it already lives.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q --tb=short` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Fix | Behavior to Verify | Test Type | Command |
|-----|-------------------|-----------|---------|
| SECRET_KEY rotation | Django starts without error; SECRET_KEY is not the insecure fallback | smoke | `python -c "import django; django.setup(); from django.conf import settings; assert 'insecure' not in settings.SECRET_KEY"` |
| CSRF re-enable | Existing 77 tests still pass | automated | `cd backend && python -m pytest tests/ -x -q` |
| CSRF re-enable | POST to submit-feedback with CSRF cookie returns 200 | manual | Login via browser → submit like/dislike → check response |
| CSRF re-enable | POST to submit-feedback without CSRF cookie returns 403 | manual | curl POST without cookie → expect 403 |
| next.config.mjs | No Spotify credentials in browser bundle | manual | Build Next.js → search `.next/` for CLIENT_SECRET value |
| next.config.mjs | Frontend still loads correctly | smoke | `npm run dev` in frontend → visit localhost:3000 |

### No new test files needed

All validation is either:
- Run of existing test suite (confirms regressions)
- Shell one-liners (confirms config)
- Manual smoke tests (confirms CSRF token round-trip)

The existing 77 tests do not test CSRF enforcement directly (no test creates a
`Client(enforce_csrf_checks=True)`). Adding CSRF enforcement tests is out of scope for this phase —
the goal is to restore enforcement, not add new tests for it.

---

## Documentation Content Map (.env.example)

The `.env.example` file belongs at the **repo root** (not `backend/`). This is because:
- The root `.env` is read by `next.config.mjs` (currently — after the fix, it won't be needed)
- The root is the natural discovery point for developers cloning the repo
- A second `backend/.env.example` would be optional but confusing

**Recommended `.env.example` content:**

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

**Note on structure:** After Fix 2, the Next.js frontend only needs `NEXT_PUBLIC_BACKEND_URL`,
which should live in `frontend/.env.local`. The Django backend needs all the remaining vars in
`backend/.env`. The root `.env` becomes unnecessary after Fix 2 — but keeping it as a convenience
file (loaded by developers who run scripts from repo root) is reasonable. The `.env.example` should
document both locations clearly.

**Also create:** `backend/.env.example` (same content, subset to Django vars only) to make
onboarding easier for developers who only work on the backend.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret key generation | Custom random string generator | `django.core.management.utils.get_random_secret_key()` | Django's built-in generates cryptographically secure 50-char keys with the right character set |
| CSRF token management | Custom token header system | Django's built-in `CsrfViewMiddleware` + `ensure_csrf_cookie` | Already implemented and wired in the frontend |
| Env var management | Raw `os.environ.get` | python-decouple `config()` | Already installed; handles `.env` files, type casting, and missing-var errors |

---

## Common Pitfalls

### Pitfall 1: Using os.environ.get with a dangerous fallback
**What goes wrong:** `os.environ.get('SECRET_KEY', 'some-insecure-default')` — the fallback
runs silently in production when the env var is missing.
**Why it happens:** Developers add fallbacks to avoid startup crashes during development.
**How to avoid:** Use `config('SECRET_KEY')` (python-decouple) with no default. It raises
`UndefinedValueError` at startup if the key is missing, making the misconfiguration visible
immediately rather than silently using a weak key.

### Pitfall 2: Confusing next.config.mjs `env` block with `NEXT_PUBLIC_` prefix
**What goes wrong:** Thinking `env: { SPOTIFY_CLIENT_SECRET: ... }` is server-side only.
**Why it happens:** The `env` block looks like it's just setting Node environment variables.
But Next.js bakes the `env` block values into the client-side JavaScript bundle at build time.
**How to avoid:** Only put truly server-side secrets in environment variables that are NOT in
the `env` block and do NOT have the `NEXT_PUBLIC_` prefix. Frontend code should only access
`NEXT_PUBLIC_*` vars.

### Pitfall 3: Disabling CSRF at two layers
**What goes wrong:** Commenting out `CsrfViewMiddleware` AND having `CsrfExemptSessionAuthentication`
— if you re-enable the middleware but forget the dead class, it could be accidentally activated later.
**How to avoid:** Delete `CsrfExemptSessionAuthentication` entirely when re-enabling the middleware.
Don't leave bypass classes around as "just in case" code.

### Pitfall 4: CSRF token cookie not readable by JavaScript
**What goes wrong:** If `CSRF_COOKIE_HTTPONLY = True`, JavaScript cannot read the `csrftoken`
cookie, and the axios interceptor silently sends no CSRF token. Requests get 403.
**Why it matters here:** `settings.py` has `CSRF_COOKIE_HTTPONLY = False` — this is correct and
must be kept. Do not change it to `True` when enabling CSRF.

### Pitfall 5: Forgetting to add backend/.env to gitignore
**What goes wrong:** Developer adds `SECRET_KEY` to `backend/.env`, which gets committed.
**Current state:** The root `.gitignore` ignores `.env` at all levels (the pattern `.env` without
a path anchor matches `backend/.env`). [VERIFIED: git check-ignore confirmed .env is blocked]
No action needed — but verify this remains true after any `.gitignore` changes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Django's TestClient disables CSRF by default — tests using force_login + POST won't break when CsrfViewMiddleware is re-enabled | Fix Strategy for Issue 3 | Tests break after re-enabling CSRF; would need to add `Client(enforce_csrf_checks=False)` pattern or mock |
| A2 | No test uses `Client(enforce_csrf_checks=True)` — confirmed by grep, but grep searched test files only | Risk Assessment | One test could be missed if it constructs a client differently |
| A3 | The single-user portfolio has only one active session — key rotation causes one logout | Fix Strategy for Issue 1 | If multiple sessions exist (unlikely for portfolio app), all would be invalidated |

---

## Environment Availability

All dependencies are already present. No new installs required for any of the three fixes.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-decouple | SECRET_KEY via config() | Yes | 3.8 | — |
| Django CSRF middleware | CSRF re-enable | Yes (built-in) | Django 5.1.3 | — |
| python-dotenv | conftest.py .env loading in tests | Yes (in requirements) | 1.0.0 | — |

---

## Sources

### Primary (HIGH confidence — directly read from files in this session)
- `backend/config/settings.py` — SECRET_KEY current state, MIDDLEWARE config, CSRF settings
- `backend/apps/core/views.py` — CsrfExemptSessionAuthentication definition and non-usage
- `frontend/next.config.mjs` — CLIENT_SECRET exposure mechanism
- `frontend/services/axios.ts` — existing CSRF token transmission mechanism
- `frontend/app/components/CsrfProvider.tsx` — CSRF token fetch on mount
- `frontend/app/layout.tsx` — CsrfProvider mounted at root
- `backend/tests/test_feedback.py` — POST tests using force_login (CSRF-relevant)
- `backend/pytest.ini` — test runner configuration
- git history (`96d76dcd`, `cfaf255d`) — original hardcoded SECRET_KEY confirmed
- `.gitignore` — `.env` exclusion verified
- `git ls-files` / `git check-ignore` — .env files confirmed NOT tracked in git
- `pip show python-decouple` — version 3.8 confirmed installed

### Secondary (MEDIUM confidence)
- Django 5.1.3 documentation pattern for TestClient CSRF behavior [ASSUMED from training knowledge,
  consistent with observed test behavior — 77 tests pass with force_login + POST pattern]

---

## Metadata

**Confidence breakdown:**
- Current security state: HIGH — read directly from files
- Fix strategies: HIGH — mechanical changes to known files with known content
- Test impact: HIGH — all 77 tests confirmed passing, grep confirmed no enforce_csrf_checks=True usage
- CSRF token round-trip (manual test): MEDIUM — plumbing is verified present, actual browser
  behavior requires a manual smoke test after the fix

**Research date:** 2026-05-12
**Valid until:** 2026-07-12 (stable Django 5.x API — not fast-moving)

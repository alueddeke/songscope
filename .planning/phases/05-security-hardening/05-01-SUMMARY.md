---
phase: 05-security-hardening
plan: 01
subsystem: backend/security
tags: [security, django, csrf, secret-key, python-decouple]
completed: "2026-05-12T17:22:00Z"
duration_minutes: 7
tasks_completed: 2
tasks_total: 2

dependency_graph:
  requires: []
  provides:
    - SECRET_KEY loaded from backend/.env via python-decouple config()
    - CsrfViewMiddleware active in MIDDLEWARE
    - CsrfExemptSessionAuthentication removed
  affects:
    - backend/config/settings.py
    - backend/apps/core/views.py
    - backend/.env (gitignored, created locally)

tech_stack:
  added: []
  patterns:
    - python-decouple config() for SECRET_KEY and DEBUG (consistent with existing Spotify credential pattern)
    - Django built-in CsrfViewMiddleware (re-enabled, no new dependency)

key_files:
  modified:
    - backend/config/settings.py
    - backend/apps/core/views.py
  created:
    - backend/.env (gitignored — contains SECRET_KEY=<freshly generated>, DEBUG=True)

decisions:
  - Use config('SECRET_KEY') with no default — fail-loud on missing key (UndefinedValueError at startup)
  - Remove import os from settings.py entirely — not needed after migration
  - Delete CsrfExemptSessionAuthentication class entirely rather than leaving as dead code

metrics:
  duration: 7 minutes
  completed_date: "2026-05-12"
  files_modified: 2
  files_created: 1 (gitignored)
---

# Phase 05 Plan 01: SECRET_KEY Rotation and CSRF Re-enable Summary

JWT auth with env-supplied SECRET_KEY via python-decouple and re-enabled CsrfViewMiddleware after removing the dead CSRF bypass class.

## What Was Built

**Task 1 — SECRET_KEY rotation (commit 41e27219):**

Replaced the insecure `os.environ.get('SECRET_KEY', 'django-insecure-fallback-dev-only')` pattern with `config('SECRET_KEY')` via python-decouple (already installed, already used for Spotify credentials). Also migrated `DEBUG` to `config('DEBUG', default=False, cast=bool)`. The `import os` line in settings.py was removed entirely as it was only used for these two variables. A fresh 50-character key was generated via `get_random_secret_key()` and stored in `backend/.env` (gitignored). The old fallback string and the historical committed key (`96d76dcd`) are now irrelevant.

**Task 2 — CSRF re-enable and dead code removal (commit 32ec1459):**

Uncommented `"django.middleware.csrf.CsrfViewMiddleware"` in the MIDDLEWARE list. Deleted the `CsrfExemptSessionAuthentication` class (dead code — grep confirmed no view ever set `authentication_classes = [CsrfExemptSessionAuthentication]`) and removed its sole `from rest_framework.authentication import SessionAuthentication` import. The existing CSRF token round-trip plumbing (CsrfProvider in frontend layout, axios X-CSRFToken header) is already wired and requires no changes. All 77 existing tests pass (Django's TestClient bypasses CSRF by default via `enforce_csrf_checks=False`).

## Acceptance Criteria Met

- `SECRET_KEY = config('SECRET_KEY')` present in settings.py — verified
- `DEBUG = config('DEBUG', default=False, cast=bool)` present in settings.py — verified
- No `os.environ.get('SECRET_KEY'` in settings.py — verified (count: 0)
- No `django-insecure-fallback-dev-only` in settings.py — verified (count: 0)
- `backend/.env` contains `SECRET_KEY=<50-char key>` — verified
- `backend/.env` contains `DEBUG=True` — verified
- `backend/.env` SPOTIFY_CLIENT_ID and OPENAI_API_KEY preserved — verified
- Django boots cleanly with new env-supplied SECRET_KEY — verified (`assert 'insecure' not in settings.SECRET_KEY` passes)
- `CsrfViewMiddleware` uncommented and active — verified (count: 1)
- No commented occurrence of CsrfViewMiddleware — verified (count: 0)
- `CsrfExemptSessionAuthentication` deleted — verified (count: 0)
- `SessionAuthentication` import deleted — verified (count: 0)
- `@ensure_csrf_cookie` still present — verified (count: 1)
- `CSRF_COOKIE_HTTPONLY = False` unchanged — verified (count: 1)
- All 77 tests pass — verified (`77 passed in 18.87s`)

## Threats Mitigated

| Threat | Status |
|--------|--------|
| T-05-01 Information Disclosure: SECRET_KEY in source | Mitigated — config('SECRET_KEY') with no fallback; new key generated |
| T-05-02 Spoofing/Tampering: CSRF disabled on POST endpoints | Mitigated — CsrfViewMiddleware active |
| T-05-03 Elevation of Privilege: CsrfExemptSessionAuthentication dead class | Mitigated — class deleted |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. No placeholder values or TODO stubs introduced.

## Threat Flags

None. No new trust boundaries or network endpoints introduced. Changes are configuration-only (env var loading and middleware activation).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 41e27219 | feat(05-01): rotate SECRET_KEY and migrate to python-decouple |
| Task 2 | 32ec1459 | feat(05-01): re-enable CsrfViewMiddleware and remove CSRF bypass dead code |

## Self-Check: PASSED

- backend/config/settings.py: FOUND
- backend/apps/core/views.py: FOUND
- .planning/phases/05-security-hardening/05-01-SUMMARY.md: FOUND
- Commit 41e27219: FOUND
- Commit 32ec1459: FOUND

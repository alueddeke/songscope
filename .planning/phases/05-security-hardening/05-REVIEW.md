---
phase: 05-security-hardening
reviewed: 2026-05-12T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/config/settings.py
  - backend/apps/core/views.py
  - frontend/next.config.mjs
  - frontend/package.json
  - frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: resolved
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This phase successfully migrated `SECRET_KEY` to `python-decouple`, removed the
`CsrfExemptSessionAuthentication` dead class and its `SessionAuthentication` import
from `views.py`, re-enabled `CsrfViewMiddleware`, stripped the `env` block from
`next.config.mjs`, and removed `dotenv` from `package.json`.

The major security goals were achieved, but two blocker-severity defects remain:
`OAUTHLIB_INSECURE_TRANSPORT` can still be left enabled in production via env var
without any guard, and nine views continue to return raw `str(e)` exception messages
to the client exposing internal stack details. Five warning-level quality issues
were also found, including nine stale imports that were not cleaned up when dead code
was removed.

---

## Critical Issues

### CR-01: `OAUTHLIB_INSECURE_TRANSPORT` set from env with no production guard

**File:** `backend/config/settings.py:16`
**Issue:** The setting is read as a plain string comparison and stored as a Python
bool at module load time. There is no check that enforces `False` when `DEBUG` is
`False`. If an operator accidentally sets `OAUTHLIB_INSECURE_TRANSPORT=True` in a
production `.env`, OAuth token exchanges proceed over plain HTTP and the Spotify
`client_secret` is transmitted without TLS. The problem is compounded because
`views.py:35-36` propagates this flag into the OS environment, making it process-wide.

```python
# settings.py:16 — current (unsafe)
OAUTHLIB_INSECURE_TRANSPORT = config('OAUTHLIB_INSECURE_TRANSPORT', 'False').lower() == 'true'

# Fix: clamp to False whenever DEBUG is off
_raw_insecure = config('OAUTHLIB_INSECURE_TRANSPORT', 'False').lower() == 'true'
OAUTHLIB_INSECURE_TRANSPORT = _raw_insecure and DEBUG  # False in production regardless of .env
```

And in `views.py:35-36`, add a hard guard:

```python
if settings.OAUTHLIB_INSECURE_TRANSPORT:
    if not settings.DEBUG:
        raise RuntimeError(
            "OAUTHLIB_INSECURE_TRANSPORT must not be set in production (DEBUG=False)."
        )
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
```

---

### CR-02: Raw exception messages leaked to API clients via `str(e)`

**File:** `backend/apps/core/views.py` — lines 96, 127, 132, 158, 163, 217, 222, 251, 816, 821, 845, 850, 1012, 1017
**Issue:** At least fourteen `JsonResponse` calls pass `str(e)` directly in the
response body. For a `SpotifyException` this leaks Spotify API error payloads; for
generic `Exception` it can expose Django model names, database paths, file paths, or
access tokens embedded in exception messages. This is an information-disclosure
vulnerability and is especially dangerous at `status=500` handlers.

Example (line 132):
```python
# Current (leaks internal details)
return JsonResponse({'error': str(e)}, status=500)
```

```python
# Fix: log the full error, return generic message to client
logger.error(f"Unexpected error in <view_name>: {str(e)}", exc_info=True)
return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
```

For `SpotifyException` at lines 127, 158, 217, 845, 1012 — where the HTTP status
is forwarded — the Spotify error body itself may contain user PII. Replace with a
sanitized message:
```python
except SpotifyException as e:
    logger.error(f"Spotify API error: {str(e)}")
    return JsonResponse({'error': 'Spotify API error'}, status=e.http_status or 502)
```

---

## Warnings

### WR-01: `CSRF_TRUSTED_ORIGINS` assigned twice — first assignment is silently overwritten

**File:** `backend/config/settings.py:29` and `85`
**Issue:** Line 29 sets `CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']`. Line
85 reassigns the same variable inside the "# CSRF settings" block, producing the
same list. The first assignment is dead code. While the end value is currently the
same, the duplication creates a maintenance trap: editing one copy without the other
will cause a subtle mismatch.

```python
# Fix: delete the early assignment at line 29-30; keep only the block at line 85.
# Remove lines 29-30 entirely.
```

---

### WR-02: `debug_auth` endpoint deployed to production without restriction

**File:** `backend/apps/core/views.py:351-357`
**Issue:** The `debug_auth` view is decorated with `@api_view` and
`@permission_classes([IsAuthenticated])` and is mapped to `/api/debug-auth/` in
`urls.py`. It returns `authenticated`, `user_id`, and `username` for any
authenticated session. This exposes internal user identifiers and confirms
authentication state to any logged-in user. A debug endpoint should either be
removed before production or restricted to staff/superuser only.

```python
# Fix: guard with DEBUG setting or staff requirement
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_auth(request):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Not found'}, status=404)
    # ... rest of view
```

---

### WR-03: `add_track_to_liked` manually decodes JSON body instead of using DRF request data

**File:** `backend/apps/core/views.py:829`
**Issue:** The view uses `json.loads(request.body.decode('utf-8'))` rather than the
DRF-provided `request.data`. This bypasses DRF's content-type negotiation and raises
an unhandled `json.JSONDecodeError` if the body is not valid JSON (the outer `except
Exception` will catch it and return a 500 instead of a 400). It also ignores the
`Content-Type` header.

```python
# Current (line 829)
payload = json.loads(request.body.decode('utf-8'))

# Fix: use DRF request.data
track_id = request.data.get("track_id")
if not track_id:
    return JsonResponse({'error': 'track_id is required'}, status=400)
```

---

### WR-04: `LOGGING` configuration is commented out — no log handler active

**File:** `backend/config/settings.py:98-110`
**Issue:** The entire `LOGGING` block is commented out. Django's default logging
sends only `ERROR` and above to stderr and may silently drop `INFO`/`WARNING` calls
emitted by the application's `logger`. All security-relevant events (OAuth state
mismatches, token refreshes, feedback errors) are logged with `logger.error()` /
`logger.info()` throughout `views.py`. If no handler is configured, these may be
lost entirely in production, removing the audit trail.

```python
# Fix: uncomment and configure the LOGGING block, or replace with:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING' if not DEBUG else 'INFO',
    },
}
```

---

### WR-05: `MetricsStrip` swallows all fetch errors silently — no error state surfaced

**File:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:38-41`
**Issue:** The catch block in `fetchMetrics` is empty (comment only). When the
`/api/recommendation-metrics/` endpoint returns a 401, 500, or a network error, the
component stays in `loading=false, metrics=null` state and renders nothing.
The user receives no feedback, and the failure is invisible. If the endpoint changes
its contract and starts returning an error body instead of `{message: 'No gems yet'}`,
the `null` guard at line 50 silently hides the breakage.

```tsx
// Fix: track error state and surface it
const [error, setError] = useState<boolean>(false);

const fetchMetrics = async (showRefreshing = false) => {
  if (showRefreshing) setRefreshing(true);
  try {
    const data = await get<Metrics>("/api/recommendation-metrics/");
    setMetrics(data);
    setError(false);
  } catch {
    setError(true);
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
};

// In render:
if (error) return null; // or a minimal error indicator
```

---

## Info

### IN-01: Nine unused imports remain in `views.py` after dead-code removal

**File:** `backend/apps/core/views.py:2-31`
**Issue:** The following imports are never referenced in any function body (confirmed
by AST analysis). They should be removed to reduce the attack surface (each import
executes module-level code) and eliminate false signals for future reviewers.

- `import time` (line 2)
- `import logging` (line 3) — `logger` is obtained via `utils.logging_config`
- `import requests` (line 5)
- `import numpy as np` (line 6)
- `from spotipy.oauth2 import SpotifyOAuth` (line 24)
- `from .models import UserPreferences` (part of line 26)
- `from apps.recommendations.feature_extractor import extract_current_user_profile, get_recommendations` (line 29)
- `from apps.recommendations.recommendation_engine import RecommendationEngine` (line 30)

```python
# Remove all eight of the above import lines / names
```

---

### IN-02: `CSRF_COOKIE_SECURE = False` assignment at line 30 is dead code

**File:** `backend/config/settings.py:30`
**Issue:** `CSRF_COOKIE_SECURE` is set to `False` on line 30, then overridden on
line 91 inside the `# CSRF settings` block. The first assignment is dead. This is
a subset of WR-01 but worth flagging separately so it is not missed when fixing
the duplicate `CSRF_TRUSTED_ORIGINS`.

```python
# Remove line 30 entirely; keep only the setting at line 91.
```

---

### IN-03: `gem_acceptance_rate` declared as `number | null` in TypeScript but the backend never sends `null`

**File:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:14`
**Issue:** The `Metrics` interface declares `gem_acceptance_rate: number | null`,
and the frontend null-guards it correctly. However, `views.py:423` always computes
`gem_liked / gem_total` (division by zero is guarded by the early return at line
417), so `gem_acceptance_rate` is always a `number` in the response. The `null`
union type adds dead UI logic (line 53-55). This is a minor accuracy issue with no
runtime impact but could mislead future maintainers.

---

### IN-04: `frontend/package.json` indent inconsistency (`lucide-react` entry)

**File:** `frontend/package.json:14`
**Issue:** The `lucide-react` dependency line uses a tab indent while all other
dependency entries use two-space indent. This is a cosmetic artifact but will
cause diff noise and may break lint/format CI if a formatter is added.

```json
// Fix: use consistent 2-space indent
    "lucide-react": "^0.454.0",
```

---

_Reviewed: 2026-05-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

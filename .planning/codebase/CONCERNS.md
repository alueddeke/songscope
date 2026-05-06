# Concerns
_Last updated: 2026-05-06_

## Summary
SongScope has significant security vulnerabilities in committed code, several guaranteed runtime crashes from logic bugs, and near-zero test coverage. Many features are partially implemented — data is collected but never used (e.g. like rates, recommendation weights). The codebase is in active development and not production-ready.

## Security Concerns

1. **Hardcoded Django SECRET_KEY committed to git** — `backend/config/settings.py:34`. Must be rotated and moved to env var.

2. **Spotify client secret exposed in browser bundle** — `SPOTIFY_CLIENT_SECRET` injected via `frontend/next.config.mjs:17` into Next.js public config. Visible to any user.

3. **`OAUTHLIB_INSECURE_TRANSPORT=1` set unconditionally** — `backend/apps/core/views.py:8` sets this at module import time, disabling HTTPS enforcement for OAuth globally.

4. **CSRF middleware commented out globally** — `backend/config/settings.py:195` has `CsrfViewMiddleware` disabled. All state-mutating endpoints unprotected.

5. **Unauthenticated debug endpoint** — `/api/debug-auth/` leaks session data, cookies, and auth state to unauthenticated callers.

6. **No HTTPS enforcement** — No production settings file, no `SECURE_SSL_REDIRECT`, no `HSTS` headers configured.

## Performance Concerns

1. **N+1 DB queries in recommendation engine** — `get_track_recommendations` loops with `get_or_create` calls. Should batch with `bulk_create` / `bulk_get_or_create`.

2. **Up to 7 sequential Spotify API calls per request** — `/api/artist-details/` makes multiple serial Spotify calls. Should parallelize with `asyncio` or `concurrent.futures`.

3. **In-memory rate limiters reset per worker** — Rate limiting state stored in process memory. Ineffective under gunicorn multi-worker or any multi-process server. Needs Redis-backed rate limiting.

## Technical Debt

1. **Duplicate `refresh_spotify_token` function** — Defined in both `views.py` and another module. Risk of divergent behavior.

2. **Missing `Count` import causing guaranteed crash** — `get_personalization_summary` uses `Count` but it's not imported. Will crash on any call.

3. **Wrong `update_weights` method signature** — Called with 2 arguments but method signature accepts 1. Will raise `TypeError` on any personalization weight update.

4. **Deprecated Spotify APIs still in use** — `sp.recommendations` and `sp.audio_features` are deprecated. Will break when Spotify removes them.

5. **Hardcoded stub data in `/api/simple-recommendations/`** — Returns hardcoded response, not real recommendations. Still live.

6. **Unreachable `except` block in `spotify_callback`** — Logic error makes exception branch dead code; auth errors silently swallowed.

7. **`Recommendation.tsx` component built but not mounted** — Component exists but is not used anywhere in the frontend.

8. **AI feedback weights stored but never applied** — `HybridRecommendationEngine` stores user weight adjustments from AI feedback but doesn't use them in scoring.

9. **`RecommendationLog.liked` never updated** — Field always `None`; `like_rate` metric in personalization summary always 0.

10. **`DailyGem.was_skipped` model field orphaned** — Field exists in model/migration but no API endpoint or frontend action sets it.

11. **Stale test import paths** — `backend/tests/` references `songscope.ai_feedback_service` (old path); moved to `apps.ai.ai_feedback_service`. Tests broken.

12. **No production settings file** — Single `settings.py` used for dev and prod. `DEBUG=True` risk.

## Incomplete / Untested Areas

- Zero frontend tests — no testing infrastructure
- Backend test suite likely broken due to stale import paths
- AI feedback loop: collected but not wired into recommendations
- Personalization: weights calculated but not applied
- Daily Gem skip tracking: model ready, no endpoint
- Like/dislike: UI state held client-side only, `RecommendationLog.liked` never persisted

## TODOs and FIXMEs
Grep results from codebase show scattered TODO comments around recommendation scoring, Spotify token refresh edge cases, and UI polish items. No centralized tracking.

## Key Observations
- Multiple guaranteed crashes exist in production paths (missing import, wrong method arity)
- Secret key and client secret are committed — both need immediate rotation
- Feature completeness is ~60%: data models and UI exist but data pipelines not fully connected
- No CI means regressions go undetected

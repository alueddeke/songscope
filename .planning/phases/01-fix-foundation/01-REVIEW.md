---
phase: 01-fix-foundation
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - backend/apps/core/models.py
  - backend/apps/core/views.py
  - backend/apps/recommendations/hybrid_recommendation_engine.py
  - backend/apps/recommendations/personalization_engine.py
  - backend/pytest.ini
  - backend/tests/__init__.py
  - backend/tests/conftest.py
  - backend/tests/run_tests.py
  - backend/tests/test_ai_feedback_service.py
  - backend/tests/test_feedback.py
  - backend/tests/test_openai_integration.py
  - backend/tests/test_personalization.py
  - backend/tests/test_recommendation.py
findings:
  critical: 7
  warning: 9
  info: 4
  total: 20
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the core models, views, two recommendation engines, pytest configuration, and all 5 test files submitted for Phase 1. The implementation contains several BLOCKERs that will cause runtime crashes or incorrect behavior in production: three missing methods on `UserProfile` are called by the hybrid engine, the `AIFeedback` model is created with wrong field names (two mismatches), and `PersonalizationEngine` is imported from a path that does not exist (`from .personalization_engine` inside the `core` package, but the file lives in `recommendations`). All test files for the AI feedback service import from a `songscope` package that does not exist on disk, so those tests will always fail with `ModuleNotFoundError`. The `submit_feedback` view contains a double-delete bug in the unlike path. Additionally the OAuth callback silently skips CSRF state validation, which is a security gap.

**Update (quick pass — `test_feedback.py` view-level tests):** WR-09 is resolved. The `DailyGem.was_liked` sync is now implemented in `submit_feedback` (views.py:594-600, 640-647) and three view-level tests (`test_view_sets_was_liked_true_on_like`, `test_view_sets_was_liked_false_on_dislike`, `test_view_clears_was_liked_on_unlike`) were added to `TestDailyGemWasLikedSync`. One new WARNING was identified in these new tests (WR-10): the DISLIKE test contains a false-positive risk due to `assertFalse(None)` passing silently.

---

## Critical Issues

### CR-01: `UserProfile` is missing `add_to_cache`, `cache_size`, `get_recommendation_weights`, `update_weights`, and `needs_update` — AttributeError at runtime

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:203-204, 719, 901, 930, 942, 948`

**Issue:** The hybrid engine calls five methods on `self.profile` (a `UserProfile` instance) that are never defined on the model. `UserProfile` (models.py) only defines `get_from_cache`, `get_cache_stats`, `clear_cache`, `update_cache`, `add_feedback`, and `remove_feedback`. Every call to these undefined methods will raise `AttributeError`:

- `self.profile.add_to_cache(final_recommendations)` — line 203
- `self.profile.cache_size()` — line 204
- `self.profile.get_recommendation_weights()` — lines 719, 901, 948
- `self.profile.update_weights(weights)` — line 930
- `self.profile.needs_update()` — line 942

The engine is actively used by `get_track_recommendations` (views.py:284), so every real recommendation request crashes at line 203 after recommendations are generated.

**Fix:** Add the missing methods to `UserProfile` in `models.py`:

```python
def add_to_cache(self, recommendations):
    self.update_cache(recommendations)

def cache_size(self):
    return len(self.data.get('cache', {}).get('recommendations', []))

def get_recommendation_weights(self):
    return self.data.get('recommendation_weights', {
        'playlist_mining': 0.3,
        'artist_network': 0.25,
        'contextual': 0.2,
        'popularity': 0.15,
        'feedback': 0.1,
    })

def update_weights(self, weights):
    self.data['recommendation_weights'] = weights
    self.save(update_fields=['data'])

def needs_update(self):
    from django.utils import timezone
    return (timezone.now() - self.updated_at).days >= 1
```

---

### CR-02: `AIFeedback.objects.create` uses wrong field names — `DatabaseError` on every AI feedback submission

**File:** `backend/apps/core/views.py:693-699`

**Issue:** The `AIFeedback` model defines:
- `original_feedback = models.TextField()`
- `ai_interpretation = models.JSONField()`
- `confidence_score = models.FloatField(default=0.0)`

The view creates the object with completely different keyword arguments:

```python
ai_feedback = AIFeedback.objects.create(
    user=request.user,
    track=track,
    original_text=feedback_text,       # wrong: field is 'original_feedback'
    interpretation=interpretation,      # wrong: field is 'ai_interpretation'
    confidence=interpretation.get(...)  # wrong: field is 'confidence_score'
)
```

Every call to `submit_ai_feedback` will raise `TypeError: AIFeedback() got unexpected keyword argument 'original_text'`.

**Fix:**
```python
ai_feedback = AIFeedback.objects.create(
    user=request.user,
    track=track,
    original_feedback=feedback_text,
    ai_interpretation=interpretation,
    confidence_score=interpretation.get('confidence', 0.0)
)
```

---

### CR-03: `PersonalizationEngine` is imported from the wrong package in `views.py` — `ImportError` at runtime

**File:** `backend/apps/core/views.py:362, 599, 627`

**Issue:** The import is:
```python
from .personalization_engine import PersonalizationEngine
```

This resolves to `apps.core.personalization_engine`, which does not exist. The actual file is `backend/apps/recommendations/personalization_engine.py`. Any request that hits `get_personalization_summary`, the unlike path in `submit_feedback`, or the new-feedback path in `submit_feedback` will raise `ImportError`.

**Fix:** Change all three occurrences to:
```python
from apps.recommendations.personalization_engine import PersonalizationEngine
```

---

### CR-04: Double-delete in unlike flow — second delete attempt on already-deleted record

**File:** `backend/apps/core/views.py:595` and `backend/apps/recommendations/personalization_engine.py:285-291`

**Issue:** When a user unlikes a track, `submit_feedback` (views.py:595) calls `existing_feedback.delete()`, then immediately calls `personalization_engine.remove_feedback_learning(track.spotify_id)` (views.py:601). Inside `remove_feedback_learning`, the engine fetches the same `UserFeedback` record and calls `feedback.delete()` again (personalization_engine.py:290). Since the record was already deleted by the view, the second `delete()` is a silent no-op in Django but represents a logic error — if the order of operations ever changes this will raise `DoesNotExist` or delete unrelated data.

**Fix:** Remove the `feedback.delete()` call from `remove_feedback_learning`. That method should only undo learning effects; the caller (the view) is responsible for deleting the DB record.

```python
def remove_feedback_learning(self, track_id: str):
    logger.info(f"Removing feedback learning for track {track_id}")
    # Learning reversal will be wired in Phase 2.
    # Do NOT delete the feedback record here — the view already did it.
```

---

### CR-05: `Track.objects.get_or_create` with no `defaults` — `IntegrityError` when new track encountered

**File:** `backend/apps/core/views.py:332`

**Issue:**
```python
track_obj = Track.objects.get_or_create(spotify_id=track['id'])[0]
```

`Track.name` and `Track.artist` are `CharField(max_length=255)` with no `blank=True`. When Django attempts to create a new `Track` record (i.e., a track not yet in the DB) using this call, the INSERT will fail with `IntegrityError` or a DB NOT NULL violation because no `name` or `artist` value is supplied and no default is set on the model.

This is hit in the recommendation logging loop inside `get_track_recommendations` (views.py:331-333) for every recommendation from a source that hasn't been seen before.

**Fix:**
```python
track_obj = Track.objects.get_or_create(
    spotify_id=track['id'],
    defaults={
        'name': track.get('name', ''),
        'artist': track.get('artist', ''),
        'album': track.get('album', ''),
    }
)[0]
```

---

### CR-06: All `test_ai_feedback_service.py` and `test_openai_integration.py` tests import from nonexistent `songscope` package — all tests fail with `ModuleNotFoundError`

**File:** `backend/tests/test_ai_feedback_service.py:41, 134` and `backend/tests/test_openai_integration.py:126`

**Issue:** All three import statements reference `songscope.ai_feedback_service`:
```python
from songscope.ai_feedback_service import FeedbackInterpreter
from songscope.ai_feedback_service import RateLimitMonitor
```

There is no `songscope` package anywhere under `backend/`. The actual module path is `apps.ai.ai_feedback_service`. These tests will raise `ModuleNotFoundError` before any test body executes, causing the entire test class to be marked as an error.

**Fix:** Replace all occurrences in both files:
```python
from apps.ai.ai_feedback_service import FeedbackInterpreter
from apps.ai.ai_feedback_service import RateLimitMonitor
```
Also update the `patch()` target strings in `test_ai_feedback_service.py` (e.g., `'songscope.ai_feedback_service.settings'` → `'apps.ai.ai_feedback_service.settings'`).

---

### CR-07: OAuth callback does not validate the `state` parameter — CSRF/open-redirect vulnerability

**File:** `backend/apps/core/views.py:65-99`

**Issue:** `spotify_login` stores the OAuth state in the session (`request.session['oauth_state'] = state`, line 60). However `spotify_callback` never reads or validates that state parameter against the one returned by Spotify. The `OAuth2Session` is reconstructed without the saved state:

```python
spotify = OAuth2Session(client_id, redirect_uri=redirect_uri)
token = spotify.fetch_token(...)  # state is never checked
```

An attacker can force a victim's browser to complete an attacker-controlled OAuth authorization code exchange by directing the victim to the callback URL. This is a textbook OAuth CSRF vulnerability (RFC 6749 §10.12).

**Fix:** Pass the saved session state when reconstructing the session, which causes `requests_oauthlib` to validate it:
```python
state = request.session.get('oauth_state')
if not state:
    return JsonResponse({'error': 'Missing OAuth state'}, status=400)
spotify = OAuth2Session(client_id, state=state, redirect_uri=redirect_uri)
token = spotify.fetch_token(
    token_url,
    client_secret=client_secret,
    authorization_response=request.build_absolute_uri()
)
```

---

## Warnings

### WR-01: `profile.data['errors']` accessed without guard — `KeyError` on pre-existing profiles

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:253, 364`

**Issue:** Both `_update_profile_data` and `_add_error` do `self.profile.data['errors'].append(...)` without checking whether the `'errors'` key exists. The key is only guaranteed to exist for profiles created by this version of `_get_or_create_profile`. Users whose `UserProfile` records predate this code will have `data` dicts without an `'errors'` key, causing a `KeyError` on the first API failure.

**Fix:** Use `.setdefault`:
```python
self.profile.data.setdefault('errors', []).append({...})
```

---

### WR-02: Duplicate `logger` definition shadows the imported one

**File:** `backend/apps/core/views.py:32, 39`

**Issue:** Line 32 imports `logger` from `utils.logging_config`, then line 39 immediately rebinds it:
```python
from utils.logging_config import logger, log_api_error, log_spotify_error  # line 32
...
logger = logging.getLogger(__name__)   # line 39 — overwrites the import
```

`log_api_error` and `log_spotify_error` are imported but never used. The intended structured logger from `utils.logging_config` is silently discarded.

**Fix:** Remove line 39 and use only the imported `logger`. Delete the unused `log_api_error` and `log_spotify_error` imports if they are not consumed elsewhere.

---

### WR-03: Duplicate `except` block in `spotify_callback` — second handler is unreachable dead code

**File:** `backend/apps/core/views.py:97-103`

**Issue:** The `try` block (lines 66-99) has two consecutive `except Exception` clauses (lines 97 and 101). Python only uses the first matching handler; the second block (lines 101-103) is completely unreachable dead code. This is also a syntax anomaly — it will not cause a runtime error, but it suggests the callback was edited carelessly and the real exception handling intent may not be achieved.

**Fix:** Remove the duplicate `except` block (lines 101-103).

---

### WR-04: `refresh_spotify_token` function defined locally but also imported from `apps.spotify.utils` — shadowing at module load time

**File:** `backend/apps/core/views.py:27, 510-531`

**Issue:** Line 27 imports `refresh_spotify_token` from `apps.spotify.utils`. Line 510 defines a different function with the same name at module scope, which silently overwrites the import for all callers within this module. The locally-defined version uses raw `requests.post` and does not use the Spotipy-based approach. Any divergence between the two implementations can cause token refresh to behave differently than the rest of the codebase expects.

**Fix:** Remove the local `refresh_spotify_token` definition and rely solely on the imported one, or explicitly rename the local variant if it is intentionally different.

---

### WR-05: `feedback_history` storage key mismatch between `UserProfile.add_feedback` and `HybridRecommendationEngine.remove_feedback`

**File:** `backend/apps/core/models.py:95-96` vs `backend/apps/recommendations/hybrid_recommendation_engine.py:846`

**Issue:** `UserProfile.add_feedback` stores entries at `self.data['feedback_history']` (top-level key). `HybridRecommendationEngine.remove_feedback` reads from `self.profile.data.get('preferences', {}).get('feedback_history', [])` (nested under `preferences`). The engine's initial data structure (lines 51-66) also stores `feedback_history` under `preferences`. The two code paths will never read/write the same list — unlikes will never find any entries to remove, and the liked-artist cleanup logic in `remove_feedback` (line 855) will always silently do nothing.

**Fix:** Pick one canonical location (recommend `data['preferences']['feedback_history']`) and update `UserProfile.add_feedback` and `UserProfile.remove_feedback` to use that path.

---

### WR-06: `submit_feedback` does not protect against `IntegrityError` from `unique_together` on non-LIKE feedback types

**File:** `backend/apps/core/views.py:587-619`

**Issue:** The view checks for existing `LIKE` feedback and handles toggling (lines 587-595). However, `UserFeedback` has `unique_together = ['user', 'track']` — one feedback record per user per track, period. If a user first submits `DISLIKE` for a track and then submits `SKIP` for the same track, the second `UserFeedback.objects.create(...)` (line 619) will raise `IntegrityError` because the unique constraint is violated. The outer `except Exception` on line 655 catches it silently and returns a 500.

**Fix:** Replace the `create` with `update_or_create`:
```python
feedback, _ = UserFeedback.objects.update_or_create(
    user=request.user,
    track=track,
    defaults={'feedback_type': feedback_type, 'track_features': {}}
)
```

---

### WR-07: `debug_auth` endpoint exposes session key and full cookie dict to unauthenticated callers

**File:** `backend/apps/core/views.py:346-355`

**Issue:** The `debug_auth` endpoint has no `@permission_classes([IsAuthenticated])` decorator. It returns `session_id` and the full `cookies` dict to any caller, authenticated or not. Session IDs and cookies are sensitive — leaking them to unauthenticated callers enables session fixation and cookie theft.

**Fix:** Either add `@permission_classes([IsAuthenticated])` or, better, remove the session and cookie fields from the response, or remove the endpoint entirely before production deployment.

---

### WR-08: `run_tests.py` imports `run_integration_tests` using `from tests.test_openai_integration` — fails when script is run as documented

**File:** `backend/tests/run_tests.py:65`

**Issue:** The script documentation says to run it as `python tests/run_tests.py` from the `backend/` directory. In that execution context, `from tests.test_openai_integration import run_integration_tests` requires `tests` to be an importable package relative to `backend/`. However the script already adds `backend_dir` to `sys.path` (line 19), so the resolution would need `backend/tests/test_openai_integration.py` to be importable as `tests.test_openai_integration` — this only works if `tests/__init__.py` exists (it does). But the failing AI feedback service import (CR-06) means `test_openai_integration.py` itself will fail to import, causing this call to raise `ImportError` rather than a clean skip.

**Fix:** After fixing CR-06, this line is still risky. Consider using a direct `import importlib` approach or moving to a pytest-only test runner to avoid path fragility.

---

### WR-09: ~~`TestDailyGemWasLikedSync` tests only exercise ORM round-trips~~ — RESOLVED

**File:** `backend/tests/test_feedback.py`

**Status:** Resolved. Three view-level tests (`test_view_sets_was_liked_true_on_like`, `test_view_sets_was_liked_false_on_dislike`, `test_view_clears_was_liked_on_unlike`) were added to `TestDailyGemWasLikedSync`. The corresponding `DailyGem.was_liked` sync blocks were implemented in `submit_feedback` (views.py:594-600 for unlike, 640-647 for LIKE/DISLIKE). Patch targets (`apps.core.views.HybridRecommendationEngine`, `apps.recommendations.personalization_engine.PersonalizationEngine`, `apps.core.views.get_spotipy_client`) are all correct. The `SpotifyToken.expires_at` fixture uses `timezone.now() + timedelta(days=3650)` — timezone-aware, correct for `DateTimeField`.

See WR-10 for a newly identified defect in one of the new tests.

---

### WR-10: `test_view_sets_was_liked_false_on_dislike` will pass even if the view never writes `DailyGem.was_liked` — false positive

**File:** `backend/tests/test_feedback.py:173-174`

**Issue:** `DailyGem.was_liked` is `None` by default (the field is nullable, and setUp creates the gem without setting it). The test posts DISLIKE and then asserts:

```python
self.assertFalse(self.gem.was_liked)    # line 173
self.assertIsNotNone(self.gem.was_liked)  # line 174
```

`assertFalse` is evaluated before `assertIsNotNone`. If the view's DailyGem sync block is not reached for any reason (e.g., the gem filter returns no results, the `if gem:` guard fails, or the feature is later removed), `was_liked` remains `None`. `self.assertFalse(None)` **passes** — Python's `bool(None)` is `False`. The `assertIsNotNone` on the next line would then catch it, but only if the test runner reaches that line after `assertFalse` already passes. This ordering means the more specific guard (`assertIsNotNone`) comes second and a silent miss is possible if future refactoring reorders assertions.

More critically: because `assertFalse(None)` passes, a complete regression (view stops writing `was_liked` entirely) would not be caught by this test. The test gives false confidence.

**Fix:** Assert the field value precisely, and put the `assertIsNotNone` check first, or use `assertEqual`:

```python
self.gem.refresh_from_db()
self.assertIsNotNone(self.gem.was_liked)   # must come first
self.assertIs(self.gem.was_liked, False)   # assertIs distinguishes False from None
```

Or more concisely:
```python
self.assertEqual(self.gem.was_liked, False)
```

`assertEqual(None, False)` fails, whereas `assertFalse(None)` passes — use `assertEqual` or `assertIs` for nullable boolean fields to avoid this trap.

---

## Info

### IN-01: `import random` duplicated inside two methods despite top-level import

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:383, 439`

**Issue:** `random` is already imported at module scope (line 18) but is re-imported inside `_get_playlist_recommendations` (line 383) and `_get_artist_network_recommendations` (line 439). The redundant local imports are harmless but confusing.

**Fix:** Remove the two local `import random` statements.

---

### IN-02: `cache_hits` and `cache_misses` fields in `get_cache_stats()` are always 0 — stats are meaningless

**File:** `backend/apps/core/models.py:64-65`

**Issue:** `get_cache_stats` reports `cache_hits` and `cache_misses` by reading `cache_data.get('hits', 0)` and `cache_data.get('misses', 0)`. No code anywhere increments these counters — `get_from_cache` and `update_cache` never write to `cache['hits']` or `cache['misses']`. The stats endpoint will always report zeros.

**Fix:** Increment the counters in `get_from_cache` (hit/miss) and `update_cache` (reset hits, increment misses).

---

### IN-03: `get_simple_recommendations` returns hardcoded fake track data including placeholder preview URLs

**File:** `backend/apps/core/views.py:476-508`

**Issue:** The view returns tracks with `preview_url: 'https://p.scdn.co/mp3-preview/...'` and `image_url: 'https://i.scdn.co/image/...'` — these are placeholder strings that will produce 404s for any frontend that tries to load them. This endpoint is described as "for testing", but it is wired into the production URL configuration and can be called by any authenticated user.

**Fix:** Either remove this endpoint or replace placeholder URLs with `None`.

---

### IN-04: `test_rate_limiting` in `TestFeedbackInterpreter` asserts `Exception` rather than the specific `RateLimitExceeded`

**File:** `backend/tests/test_ai_feedback_service.py:126-128`

**Issue:**
```python
with self.assertRaises(Exception):  # RateLimitExceeded
    interpreter.interpret_feedback("test feedback")
```

Using the base `Exception` class means the test passes even if an unrelated exception is raised (e.g., `AttributeError`, `TypeError`). The test comment acknowledges the intent is to catch `RateLimitExceeded` specifically.

**Fix:** After fixing CR-06's import path:
```python
from apps.ai.ai_feedback_service import RateLimitExceeded
with self.assertRaises(RateLimitExceeded):
    interpreter.interpret_feedback("test feedback")
```

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard + quick addendum (view-level DailyGem tests)_

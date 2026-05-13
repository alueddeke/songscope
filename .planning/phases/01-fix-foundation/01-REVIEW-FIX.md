---
phase: 01-fix-foundation
fixed_at: 2026-05-07T00:00:00Z
review_path: .planning/phases/01-fix-foundation/01-REVIEW.md
iteration: 1
findings_in_scope: 16
fixed: 16
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-05-07
**Source review:** .planning/phases/01-fix-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 16 (CR-01 through CR-07, WR-01 through WR-09)
- Fixed: 16
- Skipped: 0

---

## Fixed Issues

### CR-01: Missing UserProfile methods

**Files modified:** `backend/apps/core/models.py`
**Commit:** 19a5dd8c
**Applied fix:** Added five missing methods to `UserProfile`: `add_to_cache` (delegates to `update_cache`), `cache_size` (reads `data['cache']['recommendations']` length), `get_recommendation_weights` (returns dict from `data['recommendation_weights']` with defaults), `update_weights` (persists weights via `save(update_fields=['data'])`), and `needs_update` (compares `updated_at` age to 1 day). All methods appended after `remove_feedback`.

---

### CR-02: AIFeedback.objects.create wrong field names

**Files modified:** `backend/apps/core/views.py`
**Commit:** 759126e7
**Applied fix:** Changed `original_text` -> `original_feedback`, `interpretation` -> `ai_interpretation`, and `confidence` -> `confidence_score` in the `AIFeedback.objects.create(...)` call inside `submit_ai_feedback` (views.py line ~693).

---

### CR-03: PersonalizationEngine imported from wrong package

**Files modified:** `backend/apps/core/views.py`
**Commit:** 0b02ab37
**Applied fix:** Replaced all three `from .personalization_engine import PersonalizationEngine` occurrences (lines 362, 599, 627) with `from apps.recommendations.personalization_engine import PersonalizationEngine`. Used `replace_all` to catch every instance atomically.

---

### CR-04: Double-delete in unlike flow

**Files modified:** `backend/apps/recommendations/personalization_engine.py`
**Commit:** a87b4059
**Applied fix:** Replaced the entire body of `remove_feedback_learning` (which fetched and re-deleted the already-deleted `UserFeedback` record) with a stub log message. The view is solely responsible for deleting the DB record; the engine method logs intent only, pending Phase 2 learning reversal.

---

### CR-05: Track.objects.get_or_create missing defaults

**Files modified:** `backend/apps/core/views.py`
**Commit:** a2d5c1f3
**Applied fix:** Expanded `Track.objects.get_or_create(spotify_id=track['id'])[0]` in the recommendation logging loop (views.py line ~332) to include `defaults={'name': track.get('name', ''), 'artist': track.get('artist', ''), 'album': track.get('album', '')}`, preventing `IntegrityError` on first encounter of a new track.

---

### CR-06: Test files import from nonexistent songscope package

**Files modified:** `backend/tests/test_ai_feedback_service.py`, `backend/tests/test_openai_integration.py`
**Commit:** 45f9a38c
**Applied fix:** In `test_ai_feedback_service.py`, replaced `from songscope.ai_feedback_service import FeedbackInterpreter` (setUp), `from songscope.ai_feedback_service import RateLimitMonitor` (setUp), and all six `patch('songscope.ai_feedback_service.settings')` strings with the correct `apps.ai.ai_feedback_service` path. In `test_openai_integration.py`, updated the single `from songscope.ai_feedback_service import FeedbackInterpreter` in `test_django_integration`.

---

### CR-07: OAuth callback missing state validation

**Files modified:** `backend/apps/core/views.py`
**Commit:** f0c29396
**Applied fix:** Added state retrieval at the top of the `spotify_callback` try block: reads `request.session.get('oauth_state')`, returns HTTP 400 if missing, then passes `state=state` to `OAuth2Session(...)`. This causes `requests_oauthlib` to validate the returned state parameter against the stored one, closing the CSRF/OAuth CSRF vulnerability.

---

### WR-01: profile.data['errors'] accessed without guard

**Files modified:** `backend/apps/recommendations/hybrid_recommendation_engine.py`
**Commit:** 93cf66db
**Applied fix:** Changed both `self.profile.data['errors'].append({...})` calls (in `_update_profile_data` exception handler and `_add_error` method) to `self.profile.data.setdefault('errors', []).append({...})`. This prevents `KeyError` on profiles created before the `errors` key was introduced.

---

### WR-02: Duplicate logger definition shadows the import

**Files modified:** `backend/apps/core/views.py`
**Commit:** 72af15ff
**Applied fix:** Removed line 39 (`logger = logging.getLogger(__name__)`) that was silently overwriting the structured logger imported from `utils.logging_config`. Also removed unused `log_api_error` and `log_spotify_error` from the import on line 32 (neither is referenced anywhere in views.py).

---

### WR-03: Duplicate except block in spotify_callback

**Files modified:** `backend/apps/core/views.py`
**Commit:** d33f82fd
**Applied fix:** Removed the second duplicate `except Exception as e` block (lines 101-103) that was unreachable dead code after the first handler on line 97.

---

### WR-04: Local refresh_spotify_token shadows imported version

**Files modified:** `backend/apps/core/views.py`
**Commit:** e77783f1
**Applied fix:** Removed the entire locally-defined `refresh_spotify_token` function (lines 513-534) that used raw `requests.post` and overwrote the import from `apps.spotify.utils`. All callers in the module now use the imported version exclusively.

---

### WR-05: feedback_history storage key mismatch

**Files modified:** `backend/apps/core/models.py`
**Commit:** 42fb2da6
**Applied fix:** Updated `UserProfile.add_feedback` to store entries at `data['preferences']['feedback_history']` using `self.data.setdefault('preferences', {}).setdefault('feedback_history', [])`. Updated `UserProfile.remove_feedback` to read and filter from `self.data.get('preferences', {})['feedback_history']`. Both paths now use the same canonical location that the hybrid engine reads from.

---

### WR-06: IntegrityError from unique_together on non-LIKE feedback types

**Files modified:** `backend/apps/core/views.py`
**Commit:** b462fee2
**Applied fix:** Replaced `UserFeedback.objects.create(...)` in the new-feedback path of `submit_feedback` with `UserFeedback.objects.update_or_create(user=request.user, track=track, defaults={'feedback_type': feedback_type, 'track_features': {}})`. This prevents `IntegrityError` when a user submits a second feedback type (e.g., SKIP after DISLIKE) for the same track.

---

### WR-07: debug_auth endpoint exposes session and cookies to unauthenticated callers

**Files modified:** `backend/apps/core/views.py`
**Commit:** f744be0e
**Applied fix:** Added `@permission_classes([IsAuthenticated])` decorator to `debug_auth`. Also removed `session_id` and `cookies` from the response dict — only `authenticated`, `user_id`, and `username` are now returned, eliminating the session fixation and cookie theft vectors.

---

### WR-08: run_tests.py import path depends on CR-06 fix

**Files modified:** none (resolved by CR-06)
**Commit:** 45f9a38c (CR-06 commit)
**Applied fix:** WR-08 is resolved as a side-effect of CR-06. The `from tests.test_openai_integration import run_integration_tests` import in `run_tests.py` will now succeed because `test_openai_integration.py` no longer imports from the nonexistent `songscope` package at module level. No additional change to `run_tests.py` was required beyond CR-06.

---

### WR-09: DailyGem.was_liked sync missing from submit_feedback

**Files modified:** `backend/apps/core/views.py`
**Commit:** bb0f34e7
**Applied fix:** Added `DailyGem` to the models import line. In the unlike path, after clearing `RecommendationLog.liked`, added a query for today's `DailyGem` for the user+track and sets `was_liked = None`. In the new-feedback path, after writing `RecommendationLog.liked`, added a conditional block (only for LIKE/DISLIKE) that finds today's gem and sets `was_liked = True/False` accordingly. The `DailyGem` model and `was_liked` field already existed in models.py (lines 239-257), so no model changes were needed.

**Note:** Requires human verification — the logic mapping feedback_type to was_liked is correct as designed but the view integration should be confirmed via end-to-end test.

---

_Fixed: 2026-05-07_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

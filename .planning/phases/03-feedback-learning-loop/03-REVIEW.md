---
phase: 03-feedback-learning-loop
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - backend/tests/test_feedback_learning.py
  - backend/apps/recommendations/personalization_engine.py
  - backend/apps/recommendations/hybrid_recommendation_engine.py
  - backend/apps/core/views.py
  - backend/config/urls.py
  - backend/tests/test_recommendation_scoring.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 3 delivers three new behaviors: (1) online taste-vector updates via `PersonalizationEngine.apply_feedback_learning` / `remove_feedback_learning`, (2) Thompson Beta-bandit source weighting in `HybridRecommendationEngine.get_recommendation_weights`, and (3) a Gaussian bell-curve novelty formula replacing the old linear formula in `_score_recommendations`. The core algorithms are correctly implemented. Two blockers were found: unhandled `UserProfile.DoesNotExist` exceptions that will crash feedback processing for any user whose profile was deleted, and a probabilistically flaky test that will produce rare but real CI failures. Four warnings cover a division-by-zero when `width=0`, a stale `source_stats` write path (the bandit reads stats it can never accumulate), a misleading dead-code score initializer, and a missing `remove_feedback_learning` call for DISLIKE unlike. Three info-level items round out the review.

---

## Critical Issues

### CR-01: `UserProfile.objects.get()` raises unhandled `DoesNotExist` in feedback path

**File:** `backend/apps/recommendations/personalization_engine.py:277` and `personalization_engine.py:335`

**Issue:** Both `apply_feedback_learning` and `remove_feedback_learning` call `UserProfile.objects.get(user=self.user)` without a try/except. If the profile row was deleted (e.g., during testing, admin cleanup, or a migration error) the unhandled `UserProfile.DoesNotExist` propagates through `submit_feedback` in `views.py`, bypasses all per-method error handling there, and is only caught by the outermost `except Exception` block which returns a generic 500 to the client. Meanwhile the feedback row may already have been written to the DB, leaving it orphaned. This is especially hazardous because `views.py:504` calls `apply_feedback_learning` after `UserFeedback.objects.update_or_create` — the DB is mutated but the taste-vector update silently fails at the 500 boundary.

`HybridRecommendationEngine.__init__` correctly uses `get_or_create`; the personalization engine should mirror that pattern.

**Fix:**
```python
# personalization_engine.py — apply_feedback_learning (line 277)
try:
    profile = UserProfile.objects.get(user=self.user)
except UserProfile.DoesNotExist:
    logger.error(
        "apply_feedback_learning: no UserProfile for user %s — skipping",
        self.user.id,
    )
    return

# personalization_engine.py — remove_feedback_learning (line 335)
try:
    profile = UserProfile.objects.get(user=self.user)
except UserProfile.DoesNotExist:
    logger.error(
        "remove_feedback_learning: no UserProfile for user %s — skipping",
        self.user.id,
    )
    return
```

---

### CR-02: `test_beta_sample_increases_with_successes` is probabilistically flaky

**File:** `backend/tests/test_feedback_learning.py:294-318`

**Issue:** The test draws one sample from `Beta(6, 1)` via `random.betavariate` and asserts it exceeds 0.25 (the cold-start default for `artist_network`). After normalization against the four other cold-start sources that sum to 0.75, the assertion is:

```
beta / (0.75 + beta) > 0.25
```

Solving: this fails when `beta <= 0.333...`. `Beta(6,1)` has mean ≈ 0.857 and mode = 1.0 but non-zero density below 0.333. Empirically ~0.024% of single draws from this distribution fail the post-normalization check. In a CI pipeline running this suite thousands of times (nightly, per-PR, per-branch) this will eventually produce a spurious RED build with no code change.

**Fix:** Seed the RNG or mock `random.betavariate` to a deterministic value, or restructure the test to verify the statistical property without relying on a single draw:

```python
def test_beta_sample_increases_with_successes(self):
    engine = make_engine_with_stats("artist_network", successes=5, failures=0)
    # Run 50 draws; the mean of Beta(6,1) is 0.857 — at least 40 of 50
    # normalized weights must exceed the cold-start default 0.25.
    import random
    random.seed(42)
    above = sum(
        1 for _ in range(50)
        if engine.get_recommendation_weights().get("artist_network", 0) > 0.25
    )
    self.assertGreaterEqual(above, 45,
        msg=f"Expected most Beta(6,1) draws to exceed 0.25; got {above}/50 above threshold")
```

Alternatively, patch `random.betavariate` with `unittest.mock.patch` to return a fixed value (e.g., 0.9).

---

## Warnings

### WR-01: Division by zero when `preferred_popularity_range.width = 0`

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:859`

**Issue:** The Gaussian novelty formula is:

```python
novelty = math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))
```

If `width` is 0 (e.g., a client sends `{"preferred_popularity_range": {"midpoint": 50, "width": 0}}`), this raises `ZeroDivisionError`, crashing `_score_recommendations` for every candidate in the batch. The outer `get_recommendations` catch at line 281 swallows it and falls back to `_get_fallback_recommendations`, silently degrading service.

**Fix:**
```python
# Line 846 — after extracting width:
width = pop_range.get('width', 20)
if width == 0:
    width = 20  # guard against client-supplied zero
    logger.warning("preferred_popularity_range.width was 0; defaulting to 20")
```

---

### WR-02: `source_stats` is never written — Thompson bandit always operates in cold-start

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:89-142`

**Issue:** `get_recommendation_weights` reads `profile.data['source_stats']` to decide whether to sample from Beta or return the static default. However, no code in any of the reviewed files (or anywhere in the backend, per exhaustive grep) ever *writes* to `source_stats`. There is no call that increments `s` (successes) or `f` (failures) for any source after feedback is received. Because `source_stats` is never populated, the non-cold-start branch (`n >= COLD_START_THRESHOLD`) is permanently unreachable in production. The bandit degrades to a neutral multiplier (all weights = 1.0 via the cold-start path).

This is a completeness bug: the write path is the missing half of the bandit. It should be added in `submit_feedback` (views.py) or inside `apply_feedback_learning`, after feedback is associated with a known source via `RecommendationLog`.

**Fix (sketch):**
```python
# After apply_feedback_learning in views.py submit_feedback, retrieve the source
# from the most recent RecommendationLog for this track and update source_stats.
log = RecommendationLog.objects.filter(user=request.user, track=track) \
    .order_by('-recommended_at').first()
if log and log.source:
    source = log.source
    profile = engine.profile  # HybridRecommendationEngine instance
    source_stats = profile.data.setdefault('source_stats', {})
    stats = source_stats.setdefault(source, {'s': 0, 'f': 0})
    if feedback_type == 'LIKE':
        stats['s'] += 1
    elif feedback_type == 'DISLIKE':
        stats['f'] += 1
    profile.save(update_fields=['data'])
```

---

### WR-03: Dead score initializer in `_get_contextual_recommendations` is misleading

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:727`

**Issue:** Contextual recommendation dicts are created with `'score': 0.3` and the comment `# Boost contextual recommendations`. However, `_score_recommendations` (line 878) unconditionally overwrites `rec['score']` with the locked formula `0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier`. The pre-set value of 0.3 is never read and the stated "boost" never applies. The comment actively misleads future maintainers into believing contextual recs receive preferential scoring treatment.

**Fix:**
```python
# Line 727 — change to the same 0.0 used by all other strategies
'score': 0.0,  # will be set by _score_recommendations
```

---

### WR-04: Unlike path for DISLIKE feedback type skips `remove_feedback_learning`

**File:** `backend/apps/core/views.py:453-491`

**Issue:** `submit_feedback` checks for an existing LIKE to implement "unlike" toggling (line 459: `if feedback_type == 'LIKE' and existing_feedback:`). When this branch fires it correctly calls `remove_feedback_learning(track.spotify_id)` to reverse the taste-vector increment. However, there is no symmetric unlike path for DISLIKE feedback: if a user submits DISLIKE and there was a previous DISLIKE on the same track, `UserFeedback.update_or_create` silently overwrites it (no taste-vector correction) and there is also no "un-dislike" toggle path at all. More critically, if a user had previously LIKEd a track and then submits DISLIKE, the existing LIKE feedback row is overwritten to DISLIKE via `update_or_create` (line 495) but `remove_feedback_learning` is never called for the LIKE that was erased — the taste-vector retains the LIKE increment. The net effect is both a LIKE increment and a DISLIKE decrement are applied to the same genres for the same track.

**Fix:**
```python
# Before update_or_create, check for an existing LIKE that is being overridden by DISLIKE:
if feedback_type == 'DISLIKE':
    prior_like = UserFeedback.objects.filter(
        user=request.user, track=track, feedback_type='LIKE'
    ).first()
    if prior_like:
        personalization_engine = PersonalizationEngine(request.user)
        personalization_engine.remove_feedback_learning(track.spotify_id)
```

---

## Info

### IN-01: `COLD_START_DEFAULTS` in test does not match `SOURCE_DEFAULTS` in engine

**File:** `backend/tests/test_feedback_learning.py:286-292`

**Issue:** `TestThompsonBandit.COLD_START_DEFAULTS` lists five source keys: `playlist_mining`, `artist_network`, `contextual`, `popularity`, `feedback`. The engine's `SOURCE_DEFAULTS` (hybrid_recommendation_engine.py lines 35-41) lists: `playlist_mining`, `artist_network`, `genre_search`, `related_artists`, `contextual`. The stale keys `popularity` and `feedback` appear to be from an earlier design iteration. Because `test_beta_sample_increases_with_successes` only checks `artist_network`, the mismatch does not cause the test to fail today, but the constant is misleading documentation and would cause incorrect assertions if tests are added that enumerate all source keys.

**Fix:** Update `COLD_START_DEFAULTS` to match the current `SOURCE_DEFAULTS`:
```python
COLD_START_DEFAULTS = {
    "playlist_mining": 0.3,
    "artist_network": 0.25,
    "genre_search": 0.2,
    "related_artists": 0.15,
    "contextual": 0.1,
}
```

---

### IN-02: `add_track_to_liked` view has misleading docstring and missing input validation

**File:** `backend/apps/core/views.py:669-692`

**Issue:** The view's docstring says "Get user's name using Spotipy" — it was clearly copy-pasted from `get_user_name`. More practically, `track_id = payload.get("track_id")` may return `None` if the key is absent from the request body, and `sp.current_user_saved_tracks_add([None])` would pass `None` to the Spotify API, raising a `SpotifyException` and returning a confusing 400/500 rather than a clear 400 Bad Request.

**Fix:**
```python
def add_track_to_liked(request):
    """Add a track to the user's Spotify liked songs."""
    ...
    track_id = payload.get("track_id")
    if not track_id:
        return JsonResponse({'error': 'track_id is required'}, status=400)
    sp.current_user_saved_tracks_add([track_id])
```

---

### IN-03: Persistent debug log leaks track names and artist names at INFO level

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:273` and `hybrid_recommendation_engine.py:390`

**Issue:** Line 273 logs the `name` and `artist` of the first three recommendations on every `get_recommendations` call at `INFO` level. Line 390 logs a sample of the first 5 saved track names. In a production environment where logs are aggregated (e.g., CloudWatch, Datadog), this permanently records user listening data linked to a user ID, creating a data-retention/PII concern if the log retention policy is longer than the user's data-deletion expectation.

**Fix:** Downgrade to `DEBUG` level so these lines are suppressed in production:
```python
# Line 273
logger.debug(f"Recommendation {i+1}: {rec['name']} ...")

# Line 390
logger.debug(f"Sample liked songs: {[track['name'] for track in saved_tracks_list[:5]]}")
```

---

_Reviewed: 2026-05-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

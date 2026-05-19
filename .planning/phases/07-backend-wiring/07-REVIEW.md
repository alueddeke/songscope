---
phase: 07-backend-wiring
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/apps/core/views.py
  - backend/tests/test_feedback.py
  - backend/tests/test_metrics.py
  - backend/tests/test_views_gem_feedback.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the phase 7 backend wiring implementation: the `views.py` additions (daily gem score persistence, `compound_hit_rate` metric, `DailyGem.was_saved` wiring) and the three new test files covering feedback, metrics, and gem-view logic.

The implementation is largely correct and well-structured. The daily gem score fields (`score_breakdown`, `score_total`, `taste_vector_snapshot`), the compound hit rate metric, and the `was_saved` sync are all wired up as specced. However, one blocker-class logic error exists: `RecommendationLog.liked` is written incorrectly for `SAVE` and `SKIP` feedback types, corrupting the metric data. Three warnings round out the findings.

---

## Critical Issues

### CR-01: `SAVE` and `SKIP` feedback types corrupt `RecommendationLog.liked`

**File:** `backend/apps/core/views.py:685-690`

**Issue:** The `RecommendationLog.liked` sync block runs unconditionally for every non-unlike code path — including `SAVE` and `SKIP` feedback types. The expression `log.liked = (feedback_type == 'LIKE')` evaluates to `False` for both `SAVE` and `SKIP`. This means a user clicking "save" or "skip" silently stamps the track's recommendation log as *disliked*, corrupting the `gem_liked` / `gem_acceptance_rate` / `compound_hit_rate` metrics that query `RecommendationLog.liked`.

The comment at lines 681–684 only documents the `LIKE` → `True` / `DISLIKE` → `False` mapping and does not acknowledge `SAVE` or `SKIP`. The serializer (`FeedbackSubmissionSerializer`) explicitly accepts all four types including `SAVE`, so this path is reachable via normal API use. There are zero tests for `SAVE` or `SKIP` feedback submission, so the corruption goes undetected.

**Fix:** Guard the `RecommendationLog.liked` write to only the two types it models:

```python
# Only LIKE and DISLIKE carry liked-signal semantics.
if feedback_type in ('LIKE', 'DISLIKE'):
    log = RecommendationLog.objects.filter(
        user=request.user, track=track
    ).order_by('-recommended_at').first()
    if log:
        log.liked = (feedback_type == 'LIKE')
        log.save(update_fields=['liked'])
```

Add complementary tests for `SAVE` and `SKIP` submissions that assert `RecommendationLog.liked` is not modified.

---

## Warnings

### WR-01: Dead security branch — `OAUTHLIB_INSECURE_TRANSPORT` production guard is unreachable

**File:** `backend/apps/core/views.py:28-36`

**Issue:** The module-level guard reads:

```python
if settings.OAUTHLIB_INSECURE_TRANSPORT:
    if not settings.DEBUG:
        _logging.critical("... set OAUTHLIB_INSECURE_TRANSPORT=False.")
    else:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
```

`settings.OAUTHLIB_INSECURE_TRANSPORT` is defined in `settings.py` as `_raw_insecure and DEBUG`, which is always `False` when `DEBUG=False`. The inner `if not settings.DEBUG:` branch (lines 29–34) is therefore **dead code** — it can never execute. The intended production-safety warning is silently bypassed. More critically, if the process-level environment variable `OAUTHLIB_INSECURE_TRANSPORT=1` was set externally (e.g., from a misconfigured deployment shell), this guard does nothing to clear it. A passing OAuth token exchange over plain HTTP would succeed without any warning.

**Fix:** Remove the dead branch and add an explicit env-var reset for production:

```python
if not settings.DEBUG:
    # Ensure insecure transport is never enabled in production,
    # even if the env var was inherited from the shell.
    os.environ.pop('OAUTHLIB_INSECURE_TRANSPORT', None)
elif settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
```

### WR-02: `improvement_story` guard threshold is off — misleading metric for 2–13 gems

**File:** `backend/apps/core/views.py:452-466`

**Issue:** The guard fires when `gem_total < 2`, returning all `None`. For `gem_total` in `[2, 13]`, `first_7 = gem_list[:7]` and `last_7 = gem_list[-7:]` overlap substantially (sharing up to 6 of the same gems when `gem_total == 8`). The `delta` is always `0` when `gem_total <= 7` because `first_7` and `last_7` are identical slices. This produces a confident-looking `delta: 0` that implies "no improvement" when in reality there is not enough data to compare. The test at line 198 (`test_improvement_story_null_when_fewer_than_2_gems`) only checks `gem_total == 1` and therefore does not catch this.

**Fix:** Raise the guard threshold to match the window size:

```python
if gem_total < 14:  # Need at least 2 non-overlapping windows of 7
    improvement_story = {'first_7_rate': None, 'last_7_rate': None, 'delta': None}
```

Alternatively, document that partial overlap is acceptable and update the test to verify the overlapping behavior is intentional.

### WR-03: `AIFeedbackSubmissionSerializer.track_id` has no format validation

**File:** `backend/apps/core/views.py:717` / `backend/apps/core/serializers.py:60`

**Issue:** `FeedbackSubmissionSerializer.track_id` enforces a strict `^[A-Za-z0-9]{22}$` regex. `AIFeedbackSubmissionSerializer.track_id` is declared as `CharField(max_length=255)` with no format constraint. Any arbitrary string up to 255 characters is accepted and passed directly to `Track.objects.get(spotify_id=track_id)`. While this does not produce an injection risk (Django ORM parameterizes the query), it does mean:

1. Malformed IDs silently reach the DB lookup, wasting a query before returning 400.
2. The inconsistency between the two serializers is a maintenance trap — future callers of `submit_ai_feedback` may assume the same ID guarantees as `submit_feedback`.

**Fix:** Apply the same regex validator to the AI feedback serializer:

```python
track_id = serializers.RegexField(
    regex=r'^[A-Za-z0-9]{22}$',
    max_length=22,
    required=False,
    allow_blank=True,
    error_messages={'invalid': 'Invalid Spotify track ID format'},
)
```

---

## Info

### IN-01: `track_features` is unconditionally overwritten to `{}` on feedback update

**File:** `backend/apps/core/views.py:655-658`

**Issue:** The `update_or_create` call in `submit_feedback`'s else-branch always includes `'track_features': {}` in `defaults`. On an update (not a create), this overwrites any previously stored `track_features` dict with an empty dict. Since `track_features` is only populated during `Track` creation (the `if created:` block at line 595), and the field is not used downstream, this has no current runtime impact. However, it is a latent bug if `track_features` is ever written by another code path.

**Fix:** Remove `track_features` from the `defaults` dict to avoid overwriting on updates:

```python
feedback, _ = UserFeedback.objects.update_or_create(
    user=request.user,
    track=track,
    defaults={'feedback_type': feedback_type},
)
```

### IN-02: `TestFeedbackInterpreterSingleton` leaves mutated singleton state after test run

**File:** `backend/tests/test_views_gem_feedback.py:311-323`

**Issue:** `test_singleton_cost_accumulates` resets `interpreter.rate_limiter.daily_cost = 0.0` at the start of the test (line 315), then calls `log_cost(1000)`, leaving the singleton's `daily_cost` non-zero at the end. If any future test (in this file or loaded later in the same process) calls `get_feedback_interpreter()` and relies on `daily_cost` starting at zero, it will see stale state. Django's `TestCase` rolls back DB transactions but does not reset module-level singletons.

**Fix:** Add a `tearDown` method to reset the singleton cost after each test in the class:

```python
def tearDown(self):
    from apps.ai.ai_feedback_service import get_feedback_interpreter
    get_feedback_interpreter().rate_limiter.daily_cost = 0.0
```

---

_Reviewed: 2026-05-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

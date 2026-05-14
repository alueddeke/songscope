---
phase: 06-schema-migration
reviewed: 2026-05-14T18:45:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - backend/apps/core/migrations/0008_dailygem_score_breakdown_score_total_was_saved_taste_vector_snapshot.py
  - backend/apps/core/models.py
  - backend/tests/test_feedback.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-14T18:45:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 06 adds four new fields to `DailyGem` (`score_breakdown`, `score_total`, `was_saved`, `taste_vector_snapshot`) via migration 0008 and registers corresponding ORM round-trip tests. The migration is structurally sound: all four field definitions match the model exactly (keyword order aside), the dependency chain (`0007 → 0008`) is correct, and the schema is safe for zero-data-migration deployment because all pre-existing rows will receive either a DB-level default (`score_breakdown`) or NULL (the three nullable fields).

No security vulnerabilities or data-loss risks were found. One timing-dependent test flakiness issue rises to Warning level; three informational items are noted below.

## Warnings

### WR-01: Flaky test — `test_most_recent_log_is_picked_for_user_track` relies on wall-clock ordering

**File:** `backend/tests/test_feedback.py:56-66`

**Issue:** The test creates two `RecommendationLog` rows in rapid succession within the same transaction and then asserts that `.order_by('-recommended_at').first()` returns the second (newer) row. Both rows use `auto_now_add=True` on `DateTimeField`. On SQLite with microsecond resolution, the two `INSERT` calls may land within the same microsecond, producing identical `recommended_at` values. When timestamps are equal, `.first()` returns an arbitrary row (determined by internal cursor order), making the assertion non-deterministic and the test potentially flaky in fast CI environments.

**Fix:** Explicitly set `recommended_at` on the second row to guarantee it is strictly later, or compare PKs in `pk`-descending order when timestamps are equal:

```python
import datetime
newer_log = RecommendationLog.objects.create(user=self.user, track=self.track)
# Force a later timestamp so ordering is deterministic
RecommendationLog.objects.filter(pk=newer_log.pk).update(
    recommended_at=newer_log.recommended_at + datetime.timedelta(microseconds=1)
)
newer_log.refresh_from_db()

result = (
    RecommendationLog.objects
    .filter(user=self.user, track=self.track)
    .order_by('-recommended_at', '-pk')   # pk as stable tiebreaker
    .first()
)
self.assertEqual(result.pk, newer_log.pk)
```

Alternatively, add `'-pk'` as a secondary sort to the production query in `views.py` to make the tiebreak deterministic everywhere.

## Info

### IN-01: Redundant local `date` imports inside test methods

**File:** `backend/tests/test_feedback.py:81` and `backend/tests/test_feedback.py:129`

**Issue:** Both `TestDailyGemWasLikedSync.setUp()` (line 81) and `test_today_gem_lookup_matches_views_pattern` (line 129) contain `from datetime import date` locally. The module-level import at line 6 (`from datetime import date, timedelta`) already makes `date` available throughout the file. The local imports are dead code that add noise.

**Fix:** Remove lines 81 and 129. The module-level import at line 6 is sufficient.

### IN-02: `blank=True` on nullable `BooleanField` is semantically misleading

**File:** `backend/apps/core/models.py:292` and migration line 30

**Issue:** `was_saved = models.BooleanField(null=True, blank=True)` mirrors the pattern used for `was_liked` (line 289). `blank=True` on a `BooleanField` only affects Django form validation, not the database constraint. Because `DailyGem` is never directly rendered via a Django `ModelForm`, `blank=True` has no practical effect and its presence alongside `null=True` is confusing — it suggests the field participates in form validation when it does not. The same observation applies to `was_liked` (pre-existing), but phase 06 introduces `was_saved` with the same pattern.

**Fix:** Either drop `blank=True` from `was_saved` (and align `was_liked` for consistency) or add a comment clarifying that `blank=True` is intentional for future admin form compatibility:

```python
# null=True → three-state (True/False/unknown); blank=True for admin form compatibility
was_saved = models.BooleanField(null=True, blank=True)
```

### IN-03: New fields are not written by any current business logic — no view-level test coverage

**File:** `backend/tests/test_feedback.py:204-297`

**Issue:** `TestDailyGemNewFields` verifies only ORM round-trips: the tests write values directly to the model and confirm DB persistence. No test exercises the path where `score_breakdown`, `score_total`, `was_saved`, or `taste_vector_snapshot` are populated by production code (e.g., `get_daily_gem` or `submit_feedback`). The phase context documents this as intentional ("schema-only phase"), but it means the fields exist in the schema with no write path yet, creating a gap between the schema and any observable behavior. If a writer view is added later, its tests will need to verify the full pipeline.

**Fix:** No action required for this phase if write-path logic is deferred. Document in the phase summary that view-level integration tests for these four fields are a prerequisite for the next phase that populates them.

---

_Reviewed: 2026-05-14T18:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

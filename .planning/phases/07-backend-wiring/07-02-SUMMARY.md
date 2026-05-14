---
phase: 07-backend-wiring
plan: 02
subsystem: backend
tags: [django, views, compound-hit-rate, was-saved, metrics, tdd]
completed: "2026-05-14T21:28:39Z"
duration: "3m 50s"

dependency_graph:
  requires:
    - 07-backend-wiring/07-01  # Both modify views.py; plan 01 establishes worktree state
    - 06-schema-migration/06-02  # DailyGem.was_saved column (migration 0008)
  provides:
    - Non-fatal was_saved update in add_track_to_liked (views.py)
    - compound_hit_rate key in get_recommendation_metrics JSON response
    - TestWasSavedWiring test class (4 tests)
    - Extended TestMetricsEndpoint (6 new compound_hit_rate tests)
  affects:
    - backend/apps/core/views.py::add_track_to_liked (was_saved wiring)
    - backend/apps/core/views.py::get_recommendation_metrics (gem_list query + formula + response)
    - backend/tests/test_feedback.py (TestWasSavedWiring class added)
    - backend/tests/test_metrics.py (_make_gem helper + compound_hit_rate tests)

tech_stack:
  added: []
  patterns:
    - "Non-fatal .filter().update() for FK-traversal write (track__spotify_id) — mirrors was_liked pattern but uses bulk update not object materialization"
    - "try/except Exception: pass for non-fatal ORM side-effects (D-09 silent swallow)"
    - "Compound OR metric with is-True identity checks — consistent with gem_acceptance_rate semantics (None counts as miss)"

key_files:
  modified:
    - backend/apps/core/views.py
    - backend/tests/test_feedback.py
    - backend/tests/test_metrics.py

decisions:
  - "D-07: was_saved lookup uses track__spotify_id FK traversal via ORM filter (no raw SQL — T-07-05 mitigated)"
  - "D-08: Silent no-op when no DailyGem matches: .update() returns 0 rows, no log, no error"
  - "D-09: DB exception inside was_saved block is swallowed with bare except Exception: pass — Spotify save already succeeded"
  - "D-12: compound_hit_rate = (was_liked is True OR was_saved is True) / total — OR not AND, overlap counts once"
  - "D-13: compound_hit_rate always present in main metrics response branch (gem_total > 0 path)"

metrics:
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
  tests_added: 10
  tests_baseline: 131
  tests_final: 141
  regression_suite: "141 passed"
---

# Phase 7 Plan 02: was_saved Wiring + compound_hit_rate Summary

**One-liner:** Wired `DailyGem.was_saved=True` into `add_track_to_liked` via non-fatal `.filter().update()` after Spotify save, and added `compound_hit_rate` (`(was_liked OR was_saved) / total`, identity checks) to `get_recommendation_metrics` JSON response.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TestWasSavedWiring failing tests | 4cba906d | test_feedback.py |
| 1 (GREEN) | Non-fatal was_saved update in add_track_to_liked | affe038c | views.py |
| 2 (RED) | compound_hit_rate failing tests in TestMetricsEndpoint | 2ec70799 | test_metrics.py |
| 2 (GREEN) | compound_hit_rate in get_recommendation_metrics | 1c3227b4 | views.py |

## TDD Gate Compliance

Both tasks followed the RED/GREEN pattern:

- Task 1: `4cba906d` (RED: 4 TestWasSavedWiring tests fail on assertIs(was_saved, True)) → `affe038c` (GREEN: all 4 pass)
- Task 2: `2ec70799` (RED: compound_hit_rate tests fail with KeyError) → `1c3227b4` (GREEN: all 13 TestMetricsEndpoint tests pass)

## What Was Built

### Non-fatal `was_saved` update in `add_track_to_liked` (views.py line ~843-857)

Immediately after `sp.current_user_saved_tracks_add([track_id])` and before the success response, a non-fatal try/except block was added:

```python
try:
    today = timezone.localdate()
    DailyGem.objects.filter(
        user=request.user, date=today, track__spotify_id=track_id
    ).update(was_saved=True)
except Exception:
    pass
```

Key design choices (per PATTERNS.md Pattern 4):
- Uses `.filter().update()` (bulk update, no object materialization) — correct for FK traversal
- Returns 0 rows silently when no DailyGem matches the saved track (D-08 no-op)
- Scoped to `user=request.user` — prevents cross-user write (mitigates T-07-08)
- `except Exception: pass` — DB errors silently swallowed, response always 200 (D-09)

### `compound_hit_rate` in `get_recommendation_metrics` (views.py)

Three edits:

1. Added `'was_saved'` to `gem_list` `.values()` query (prevents KeyError at runtime — RESEARCH Pitfall 2)
2. Added computation after `gem_acceptance_rate`:
   ```python
   compound_hits = sum(1 for g in gem_list if g['was_liked'] is True or g['was_saved'] is True)
   compound_hit_rate = compound_hits / gem_total
   ```
3. Added `'compound_hit_rate': compound_hit_rate` to the `JsonResponse` dict (next to `gem_acceptance_rate`)

Formula semantics:
- `is True` identity check — `None` and `False` both count as misses (consistent with `gem_acceptance_rate`)
- OR logic — overlap (both liked and saved) counts as one hit, not two (D-12)
- Always present when `gem_total > 0`; "No gems yet" early-return path unchanged (D-13)

### Test additions

`TestWasSavedWiring` (test_feedback.py): 4 tests covering matching track sets `was_saved=True`, no-op on non-match, non-fatal on DB exception (response still 200 `'all good'`), and Spotify API called exactly once.

`TestMetricsEndpoint` extensions (test_metrics.py): `_make_gem` helper updated with `was_saved=None` kwarg; `required_fields` list updated to include `compound_hit_rate`; 6 new test methods (`test_compound_hit_rate_key_present_in_response`, `test_compound_hit_rate_all_liked`, `test_compound_hit_rate_disjoint_or`, `test_compound_hit_rate_liked_and_saved_overlap_counts_once`, `test_compound_hit_rate_zero_hits`, `test_compound_hit_rate_none_is_miss`).

## Requirements Completed

| Requirement | Status | Verified By |
|-------------|--------|-------------|
| METRIC-02 | Complete | TestMetricsEndpoint::test_compound_hit_rate_* (6 methods) + test_response_includes_all_phase4_fields |

## Phase 7 Closure

All 6 Phase 7 requirements (SCHEMA-02, SCHEMA-03, SCHEMA-04, EXPLAIN-01, EXPLAIN-02, METRIC-02) are now satisfied:
- SCHEMA-02, SCHEMA-03, SCHEMA-04, EXPLAIN-01, EXPLAIN-02: completed in Plan 07-01
- METRIC-02: completed in this plan (07-02)

Full backend test suite: 141 passed, 0 regressions. Phase 7 is ready for `/gsd-verify-work 07`.

## Deviations from Plan

None — plan executed exactly as written. All `must_haves.truths` are verifiable via the test suite and grep.

## Known Stubs

None. Both `was_saved` write path and `compound_hit_rate` metric are fully wired; no placeholder values.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's threat_model already covers (T-07-05, T-07-06, T-07-07, T-07-08 all mitigated as specified).

## Self-Check

### Files Exist
- `backend/apps/core/views.py` — modified
- `backend/tests/test_feedback.py` — modified
- `backend/tests/test_metrics.py` — modified
- `.planning/phases/07-backend-wiring/07-02-SUMMARY.md` — this file

### Commits Exist
- `4cba906d` — test(07-02): add failing TestWasSavedWiring tests (RED)
- `affe038c` — feat(07-02): wire non-fatal was_saved update in add_track_to_liked
- `2ec70799` — test(07-02): add failing compound_hit_rate tests to TestMetricsEndpoint (RED)
- `1c3227b4` — feat(07-02): add compound_hit_rate to get_recommendation_metrics

## Self-Check: PASSED

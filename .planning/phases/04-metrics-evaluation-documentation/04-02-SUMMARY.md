---
phase: 04-metrics-evaluation-documentation
plan: "02"
subsystem: backend-api
tags: [backend, django, metrics, api, jaccard, rolling-window, tdd, wave-1]
dependency_graph:
  requires:
    - 04-01 (test stubs + recharts)
  provides:
    - GET /api/recommendation-metrics/ — 12-field metrics response
    - GET /api/recommendation-trend/ — rolling 7-day like-rate trend data
    - _jaccard_distance() module-level helper (unit-testable)
  affects:
    - backend/apps/core/views.py
    - backend/config/urls.py
    - backend/tests/test_metrics.py
tech_stack:
  added:
    - django.db.models.Avg (for avg_popularity DB aggregation)
    - itertools.combinations (for pairwise Jaccard diversity)
  patterns:
    - On-the-fly metrics from DailyGem + UserProfile (no new DB columns, D-01)
    - Pure-function module-level helper (_jaccard_distance) for unit-testability
    - Rolling 7-day window using date arithmetic (timedelta(days=6))
    - IsAuthenticated decorator on both endpoints (T-04-05 mitigated)
key_files:
  created: []
  modified:
    - backend/apps/core/views.py
    - backend/config/urls.py
    - backend/tests/test_metrics.py
decisions:
  - "gem_acceptance_rate returns numeric 0.0 when no feedback exists (not None); None reserved for zero-gem branch only"
  - "novel_track_rate reuses hidden_gem_rate value — was_novel field always True (Pitfall 4); field satisfies LOCKED interface without inventing unreliable computation"
  - "improvement_story returns all-None when gem_total < 2 (cold-start); overlapping first/last windows accepted for 2..13 gems per spec"
  - "diversity_score returns None when fewer than 2 gems have non-empty Track.genres (Track.genres only populated after feedback, not at DailyGem creation)"
  - "Tasks 1 and 2 committed atomically in one commit — both tasks modify the same three files and implementation was written in a single batch"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-12"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 4 Plan 02: Backend Metrics Endpoints (Wave 1) Summary

Two authenticated GET endpoints implementing on-the-fly recommendation metrics from DailyGem + UserProfile data — no new DB columns — with 15 passing tests across 4 test classes replacing all RED stubs from 04-01.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement get_recommendation_metrics + _jaccard_distance + TestMetricsEndpoint/TestTasteVector/TestJaccard GREEN | 7fe39368 | backend/apps/core/views.py, backend/config/urls.py, backend/tests/test_metrics.py |
| 2 | Implement get_recommendation_trend + URL route + TestTrendEndpoint GREEN | 7fe39368 | (same commit — see deviation note) |

## What Was Built

### Endpoint 1: GET /api/recommendation-metrics/

Registered at `path('api/recommendation-metrics/', ..., name='recommendation_metrics')`.

**Final response shape (when gems exist):**
```json
{
  "total_recommended": 12,
  "avg_popularity": 43,
  "novel_track_rate": 0.4,
  "hidden_gem_rate": 0.4,
  "gem_total": 5,
  "gem_liked": 2,
  "gem_disliked": 1,
  "gem_acceptance_rate": 0.4,
  "top_genres": ["indie pop", "rock", ...],
  "top_genres_pct": [{"genre": "indie pop", "pct": 60.0}, ...],
  "improvement_story": {
    "first_7_rate": 14,
    "last_7_rate": 71,
    "delta": 57
  },
  "diversity_score": 0.6667
}
```

**Cold-start response (0 gems):**
```json
{"message": "No gems yet"}
```

**Cold-start handling per branch:**
- 0 gems: returns `{'message': 'No gems yet'}` immediately (early exit)
- 1 gem: returns full response; `improvement_story` all-None (gem_total < 2 branch)
- 2..13 gems: `improvement_story` uses potentially-overlapping first-7/last-7 windows (per spec, overlap is acceptable)
- `diversity_score`: None when fewer than 2 gems have non-empty `Track.genres`

### Endpoint 2: GET /api/recommendation-trend/

Registered at `path('api/recommendation-trend/', ..., name='recommendation_trend')`.

**Final response shape (≥2 gem dates):**
```json
{
  "data": [
    {"date": "2026-05-03", "like_rate": 42.9},
    ...
  ]
}
```

**Cold-start response (<2 distinct gem dates):**
```json
{"data": [], "message": "Not enough data"}
```

**Cold-start handling per branch:**
- 0 or 1 distinct dates: returns `{'data': [], 'message': 'Not enough data'}`
- ≥2 dates: returns data list with one point per gem date; each point is 7-day rolling window [d-6, d]

### _jaccard_distance Helper

Module-level function at `backend/apps/core/views.py:386`, importable as:
```python
from apps.core.views import _jaccard_distance
```

Semantics: `1 - |A ∩ B| / |A ∪ B|` on set(genres_a), set(genres_b). Both empty → 0.0.

## Test Count

| Class | Base | Tests | Status |
|-------|------|-------|--------|
| TestMetricsEndpoint | django.test.TestCase | 7 | PASSED |
| TestTrendEndpoint | django.test.TestCase | 3 | PASSED |
| TestJaccard | unittest.TestCase | 3 | PASSED |
| TestTasteVector | django.test.TestCase | 2 | PASSED |
| **Total** | | **15** | **15 passed** |

Full backend suite: **77 passed** (no regressions).

## Deviations from Plan

### Implementation Deviation: Tasks 1 and 2 in a Single Commit

**Found during:** Task execution
**Issue:** Both tasks modify the exact same three files (`views.py`, `urls.py`, `test_metrics.py`). Writing code in two separate file-editing passes and committing between them would produce identical git diffs — `get_recommendation_trend` and `TestTrendEndpoint` were written at the same time as the Task 1 code since all the context was assembled together.
**Fix:** Tasks 1 and 2 committed in one atomic commit (7fe39368) covering all implementations, URL routes, and tests.
**Impact:** Functionally identical to two separate commits; all acceptance criteria satisfied independently.

### Data Model Reality: Track.genres Sparsity

**Noted during:** Implementation — consistent with Pitfall 1 in 04-RESEARCH.md
**Issue:** `Track.genres` is only populated when a user explicitly LIKE/DISLIKEs a track (which triggers a Spotify artist lookup). DailyGem creation does not fetch genres.
**Result:** In production, `diversity_score` will return `None` until the user has given feedback on at least 2 gems whose Tracks have genres populated.
**Mitigation:** Documented in code (comment in view). `null` diversity_score is the correct sentinel — the frontend DiversityScore component handles null gracefully.

## Known Stubs

None. All test stubs from 04-01 replaced with real assertions. Both endpoints fully implemented.

## Threat Surface Scan

Both endpoints use `@permission_classes([IsAuthenticated])` — unauthenticated requests return 403 (verified by TestMetricsEndpoint.test_unauthenticated_returns_403 and TestTrendEndpoint.test_unauthenticated_returns_403). All ORM queries filtered strictly on `request.user` — no cross-user data leak. T-04-05 and T-04-06 mitigated as planned.

No new threat surface beyond what was in the plan's threat model.

## Self-Check: PASSED

- `backend/apps/core/views.py` contains `def get_recommendation_metrics`: FOUND (line 405)
- `backend/apps/core/views.py` contains `def get_recommendation_trend`: FOUND (line 501)
- `backend/apps/core/views.py` contains `def _jaccard_distance`: FOUND (line 386)
- `backend/config/urls.py` contains `recommendation-metrics`: FOUND (line 53)
- `backend/config/urls.py` contains `recommendation-trend`: FOUND (line 54)
- `backend/tests/test_metrics.py` has 15 passing tests: VERIFIED
- Commit 7fe39368 exists: FOUND
- Full suite 77 passed: VERIFIED

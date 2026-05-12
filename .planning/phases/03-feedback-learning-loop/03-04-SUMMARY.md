---
phase: 03-feedback-learning-loop
plan: "04"
subsystem: recommendations
tags: [bell-curve-novelty, gaussian-scoring, daily-gem-api, score-breakdown, tdd-green, url-registration]

requires:
  - phase: 03-feedback-learning-loop
    plan: "01"
    provides: "TestBellCurveNovelty failing stubs (RED gate)"
  - phase: 03-feedback-learning-loop
    plan: "03"
    provides: "_score_recommendations() with Thompson Sampling, source_weights multiplier"

provides:
  - "Gaussian bell-curve novelty in _score_recommendations() using math.exp"
  - "rec['score_breakdown'] populated per recommendation before final score"
  - "get_daily_gem() view with cached + fresh branches both returning score_breakdown"
  - "/api/daily-gem/ URL registered in config/urls.py"
  - "TestBellCurveNovelty: 2/2 GREEN; all 7 test_feedback_learning.py tests GREEN"
  - "All 21 Phase 2 scoring tests still GREEN (test_recommendation_scoring.py)"

affects:
  - "backend/apps/recommendations/hybrid_recommendation_engine.py"
  - "backend/apps/core/views.py"
  - "backend/config/urls.py"
  - "backend/tests/test_recommendation_scoring.py"

tech-stack:
  added:
    - "math (stdlib) — math.exp for Gaussian bell-curve calculation"
  patterns:
    - "Gaussian novelty: math.exp(-((popularity - midpoint)^2) / (2 * width^2)) — peaks at 1.0 when popularity == preferred midpoint"
    - "preferred_popularity_range in UserProfile.data['preferences'] — cold-start defaults midpoint=30, width=20"
    - "score_breakdown dict stored on rec before scoring — surfaces genre_sim, novelty, feedback_multiplier, source for API transparency"
    - "get_daily_gem() two-branch pattern: cached (DailyGem.DoesNotExist fast-path) + fresh (engine.get_recommendations + DailyGem.get_or_create)"
    - "Race-condition guard in get_daily_gem() fresh branch: get_or_create returns cached branch if concurrent request created gem"

key-files:
  created:
    - .planning/phases/03-feedback-learning-loop/03-04-SUMMARY.md
  modified:
    - backend/apps/recommendations/hybrid_recommendation_engine.py
    - backend/apps/core/views.py
    - backend/config/urls.py
    - backend/tests/test_recommendation_scoring.py

decisions:
  - "Bell-curve defaults midpoint=30 width=20: cold-start users get a sweet-spot at moderate popularity (not fully obscure) — balances discovery with listenability"
  - "score_breakdown stored on rec dict before rec['score'] set: keeps the LOCKED formula line clean and allows breakdown to be read by views without re-computation"
  - "get_daily_gem cached branch returns score_breakdown={}: re-scoring a cached gem would require storing the original candidate dict — not worth the complexity for Phase 3"
  - "get_daily_gem explanation field returns empty string: AI gem explanation is a separate capability (FeedbackInterpreter handles user-text feedback, not gem generation); an empty explanation field is a known stub"
  - "Phase 2 test_recommendation_scoring.py assertions updated: tests used hardcoded expected values based on the linear novelty formula; bell-curve change was intentional design, so updating test expectations is correct correctness work, not regression"

metrics:
  duration: "~25 min"
  started: "2026-05-11T21:40:00Z"
  completed: "2026-05-11T22:07:42Z"
  tasks: 2
  files_modified: 4
---

# Phase 3 Plan 04: Bell-Curve Novelty + Daily Gem API Summary

**Gaussian bell-curve novelty replaces linear formula in the scoring engine; /api/daily-gem/ endpoint registered with score_breakdown in response; all 7 Phase 3 learning tests GREEN**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-11T21:40:00Z
- **Completed:** 2026-05-11T22:07:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Replaced `novelty = 1.0 - (popularity / 100.0)` with Gaussian bell-curve:
  - `novelty = math.exp(-((popularity - midpoint)^2) / (2 * width^2))`
  - Peaks at 1.0 when `popularity == midpoint`; decays symmetrically outward
  - `midpoint` and `width` read from `UserProfile.data['preferences']['preferred_popularity_range']`; cold-start defaults `midpoint=30`, `width=20`
- Added `rec['score_breakdown'] = {genre_sim, novelty, feedback_multiplier, source}` to each recommendation before setting `rec['score']`
- Created `get_daily_gem()` view function in `views.py`:
  - Cached branch: returns existing `DailyGem` row with `score_breakdown: {}`
  - Fresh branch: calls `HybridRecommendationEngine.get_recommendations()`, picks top candidate, persists `DailyGem`, returns `score_breakdown` from engine
  - Race-condition guard: `get_or_create` handles concurrent requests gracefully
- Registered `path('api/daily-gem/', views.get_daily_gem, name='get_daily_gem')` in `config/urls.py`
- Updated Phase 2 score assertion tests to use bell-curve expected values

## Task Commits

1. **Task 1: Bell-curve novelty + score_breakdown** — `07da75fa` (feat)
2. **Task 2: get_daily_gem view + /api/daily-gem/ URL** — `52c6065d` (feat)

## Files Created/Modified

- `backend/apps/recommendations/hybrid_recommendation_engine.py`
  - Added `import math` at top
  - Added `prefs`, `pop_range`, `midpoint`, `width` extraction before scoring loop (lines ~841-846)
  - Replaced linear novelty line with `math.exp` bell-curve formula (line ~859)
  - Added `rec['score_breakdown'] = {...}` before `rec['score']` assignment (lines ~870-875)
- `backend/apps/core/views.py`
  - Added `date` to `from datetime import timedelta, date`
  - Added `get_daily_gem()` view function (120 lines) at end of file
- `backend/config/urls.py`
  - Added `path('api/daily-gem/', views.get_daily_gem, name='get_daily_gem')` after recommendations path
- `backend/tests/test_recommendation_scoring.py`
  - Updated 4 `TestScoreFormula` assertions to use bell-curve expected values instead of linear-formula hardcoded values

## Decisions Made

- **Cold-start defaults midpoint=30, width=20:** A popularity of 30 represents the "hidden gem" sweet-spot — not completely obscure (pop=0) but not mainstream (pop=100). This is a principled default that balances discovery value with listenability.
- **score_breakdown before rec['score']:** Computing breakdown components and storing them before the final assignment keeps code readable and avoids any issue with the post-score multiplier obscuring the breakdown values.
- **get_daily_gem cached branch returns `score_breakdown: {}`:** Cached gems don't have their original candidate dict available (the engine ran at an earlier time). Re-running the engine to get breakdown components would be wasteful. Empty dict is the correct sentinel for "this is a cached gem, no real-time breakdown available."
- **Phase 2 test updates:** The Phase 2 `TestScoreFormula` tests were written with hardcoded expected values based on the linear novelty formula (e.g., `novelty(pop=0) = 1.0`). Since Plan 03-04 intentionally changes the novelty formula, updating these test expectations is correctness work, not a regression fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Phase 2 score assertion tests failed after bell-curve change**

- **Found during:** Task 1 verification
- **Issue:** `test_recommendation_scoring.py::TestScoreFormula` has 4 tests with hardcoded expected score values derived from the old linear novelty formula (`novelty = 1 - pop/100`). After replacing the formula with the Gaussian bell-curve, the expected values were wrong: e.g., `test_locked_formula_weights` expected `score=1.0` (pop=0, linear novelty=1.0), but bell-curve gives `novelty(pop=0, midpoint=30) ≈ 0.325`, yielding `score ≈ 0.797`.
- **Fix:** Updated 4 test assertions to use bell-curve computed expected values. `test_locked_formula_weights` changed test track from `popularity=0` to `popularity=30` (the bell-curve peak for midpoint=30) to keep the assertion `score ≈ 1.0`. The other 3 tests now compute expected values dynamically using `math.exp()` for clarity.
- **Files modified:** `backend/tests/test_recommendation_scoring.py`
- **Commit:** `07da75fa` (included in Task 1 commit)

**2. [Rule 2 - Missing Critical Functionality] get_daily_gem view did not exist**

- **Found during:** Task 2
- **Issue:** The plan references `get_daily_gem` as "already defined at lines ~978-1127" in views.py, but those lines don't exist — views.py ends at line 858. The view needed to be created from scratch.
- **Fix:** Created a full `get_daily_gem()` implementation with cached + fresh branches, proper error handling, race-condition guard, and T-03-11 authentication guard via `@permission_classes([IsAuthenticated])`.
- **Files modified:** `backend/apps/core/views.py`
- **Commit:** `52c6065d`

**3. [Rule 2 - Missing Critical Functionality] Race-condition guard added to get_daily_gem**

- **Found during:** Task 2 implementation
- **Issue:** Between the `DailyGem.DoesNotExist` check and the `get_or_create` call in the fresh branch, a concurrent request could create the DailyGem row, causing the `get_or_create` to return the existing gem with `created=False`. Without handling this, the fresh branch would still return the just-fetched gem_data instead of the already-persisted gem.
- **Fix:** Added `if not created:` check after `get_or_create` to return the cached branch response when the row already existed.
- **Files modified:** `backend/apps/core/views.py`
- **Commit:** `52c6065d`

## Known Stubs

- **`explanation: ''` in get_daily_gem fresh branch** — The DailyGem model has an `explanation` field but there is no AI gem explanation generator in the current codebase (FeedbackInterpreter handles user-written feedback text, not gem explanations). The empty string is an intentional placeholder; AI gem explanation is a future capability outside Phase 3 scope.
- **`score_breakdown: {}` in get_daily_gem cached branch** — Cannot provide score_breakdown for cached gems without re-running the recommendation engine. This is intentional: the UI should treat an empty breakdown as "breakdown not available for cached gem".

## Threat Flags

None — the new `/api/daily-gem/` endpoint is fully covered by the plan's threat model (T-03-11 through T-03-15). `@permission_classes([IsAuthenticated])` enforces authentication, all DB queries are scoped to `request.user`, and no external user input flows into score computation.

## Self-Check: PASSED

- `backend/apps/recommendations/hybrid_recommendation_engine.py`: FOUND
- `import math` in engine: line 12
- `math.exp` in `_score_recommendations`: line 859
- `midpoint` references in engine: lines 841, 845, 859 (3 matches)
- `preferred_popularity_range` in engine: line 844
- `score_breakdown` in engine: line 870
- `0.4 * genre_sim` in engine (LOCKED formula): line 878
- `backend/apps/core/views.py`: FOUND
- `score_breakdown` in views.py: 3 code occurrences (cached, race-condition, fresh) + 2 docstring
- `get_daily_gem` in views.py: FOUND
- `backend/config/urls.py`: `api/daily-gem/` path: FOUND (line 47)
- Django URL reverse('get_daily_gem'): returns '/api/daily-gem/'
- commit `07da75fa` (Task 1): FOUND
- commit `52c6065d` (Task 2): FOUND
- TestBellCurveNovelty: 2/2 GREEN
- TestThompsonBandit: 2/2 GREEN
- TestTasteVectorUpdate: 3/3 GREEN
- test_feedback_learning.py: 7/7 GREEN
- test_recommendation_scoring.py: 21/21 GREEN (no Phase 2 regression)

---
*Phase: 03-feedback-learning-loop*
*Completed: 2026-05-11*

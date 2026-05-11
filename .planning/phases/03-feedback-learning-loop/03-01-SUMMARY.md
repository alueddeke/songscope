---
phase: 03-feedback-learning-loop
plan: "01"
subsystem: testing
tags: [tdd, pytest, django-test, thompson-bandit, bell-curve-novelty, taste-vector]

requires:
  - phase: 02-user-taste-vector-real-scoring
    provides: HybridRecommendationEngine._score_recommendations, PersonalizationEngine.apply_feedback_learning, UserProfile.data schema

provides:
  - Failing test stubs (RED) for three Phase 3 learning behaviors
  - TDD gate for taste-vector online update, Thompson bandit source sampling, bell-curve novelty scoring
  - openai declared and importable in virtualenv

affects:
  - 03-02 (implements taste-vector update — makes TestTasteVectorUpdate green)
  - 03-03 (implements Thompson bandit — makes TestThompsonBandit green)
  - 03-04 (implements bell-curve novelty — makes TestBellCurveNovelty green)

tech-stack:
  added: []
  patterns:
    - "Django TestCase for DB-integrated tests (transaction rollback isolation per T-03-01)"
    - "HybridRecommendationEngine.__new__() bypass pattern for pure unit tests (from test_recommendation_scoring.py)"
    - "make_engine_with_stats() and make_engine_with_prefs() helpers for mocked engine state"

key-files:
  created:
    - backend/tests/test_feedback_learning.py
  modified: []

key-decisions:
  - "test_remove_feedback_reverses_like asserts post-remove < post-like (not just <= initial) to stay RED against no-ops that leave both unchanged"
  - "Thompson cold-start test uses 'bandit_active' key assertion to force RED until Phase 3 wires get_recommendation_weights() on the engine itself"
  - "openai already pinned at 1.99.9 in requirements.txt — no version change; installed 2.36.0 satisfies >=1.0.0 at env level"

patterns-established:
  - "TDD RED gate: write assertions against desired behaviour that current no-op code fails; use assertGreater/assertLess not assertRaises"
  - "DB tests: Django TestCase + refresh_from_db() to verify persistence; unit tests: Mock + profile.data dict"

requirements-completed:
  - PHASE3-LEARNING

duration: 18min
completed: 2026-05-11
---

# Phase 3 Plan 01: TDD Red-Gate Stubs Summary

**7 failing test stubs across 3 test classes gate-enforcing taste-vector online update, Thompson Beta bandit source sampling, and bell-curve novelty scoring before any Phase 3 implementation begins**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-11T21:10:00Z
- **Completed:** 2026-05-11T21:28:00Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Created backend/tests/test_feedback_learning.py with 7 test methods across 3 classes
- All 7 tests fail (RED) against current no-op personalization engine code
- Confirmed openai==1.99.9 already declared in requirements.txt; installed and importable in virtualenv

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing test stubs for all three Phase 3 behaviors** - `a2a97815` (test)
2. **Task 2: Ensure openai is in requirements.txt** - No commit needed (already present; pip install run to verify importability)

**Plan metadata:** committed in SUMMARY commit below

## Files Created/Modified
- `backend/tests/test_feedback_learning.py` - 7 failing TDD stubs: TestTasteVectorUpdate (3 DB tests), TestThompsonBandit (2 unit tests), TestBellCurveNovelty (2 unit tests)

## Decisions Made
- `test_remove_feedback_reverses_like` must assert `post_remove < post_like` (not `<= initial`) because with both methods as no-ops, post_like == initial == post_remove, so `<=` passes trivially — only `<` forces RED.
- Thompson cold-start test adds assertion for a `bandit_active` key in the returned dict to ensure the test stays RED until the engine-level `get_recommendation_weights()` is properly wired with bandit logic; it would otherwise pass trivially since the static-default path already works.
- openai requirements.txt entry (`openai==1.99.9`) left unchanged; pip installed 2.36.0 (which satisfies `>=1.0.0`).

## Deviations from Plan

None - plan executed exactly as written. The test revision to `test_remove_feedback_reverses_like` was necessary correctness work to maintain the RED state (the initial assertion `assertLessEqual(post_remove, initial)` passed trivially due to both methods being no-ops).

## Issues Encountered
- `test_remove_feedback_reverses_like` initially passed because `assertLessEqual(post_remove, initial)` is trivially satisfied when both `apply_feedback_learning` and `remove_feedback_learning` are no-ops (no value changes, so post_remove == initial). Fixed by changing to `assertLess(post_remove, post_like)`, which fails when no-op leaves post_remove == post_like.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RED gate established: 7 tests must be made green by plans 03-02, 03-03, 03-04
- 03-02 should target TestTasteVectorUpdate (taste-vector online update in apply_feedback_learning + remove_feedback_learning)
- 03-03 should target TestThompsonBandit (Beta sampling in get_recommendation_weights on HybridRecommendationEngine)
- 03-04 should target TestBellCurveNovelty (Gaussian novelty formula in _score_recommendations with preferred_popularity_range)

---
*Phase: 03-feedback-learning-loop*
*Completed: 2026-05-11*

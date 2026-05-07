---
phase: 01-fix-foundation
plan: 03
subsystem: api
tags: [django, spotipy, recommendation-engine, candidate-generation, orm]

# Dependency graph
requires:
  - phase: 01-fix-foundation/01-01
    provides: pytest infrastructure and test stubs (TestPersistentExclusionSet, TestFilterOutLikedSongs, TestRelatedArtistStrategy)
provides:
  - DB-backed persistent exclusion set replacing live Spotify API calls in candidate filter
  - Refactored _filter_out_liked_songs with no artist-name filter and no API calls
  - 5th candidate generation strategy using sp.artist_related_artists()
affects: [02-ml-scoring, 03-bandits]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Local ORM imports inside helper methods to avoid circular import risk (Pattern 1)"
    - "DB-backed set materialized via set() for O(1) membership checks"
    - "Strategy loop gated by _check_rate_limit() per iteration for graceful degradation"

key-files:
  created: []
  modified:
    - backend/apps/recommendations/hybrid_recommendation_engine.py

key-decisions:
  - "DB-backed exclusion set over live Spotify API: eliminates rate limit burn and stale-cache fallback path"
  - "Remove top-artist name filter: track-level exclusion is correct precision; artist filter blocked valid deep cuts"
  - "Local imports of RecommendationLog/DailyGem inside _get_persistent_exclusion_set: matches Pattern 1, avoids circular imports"
  - "artist_related_artists used directly in hybrid engine (not via track_discovery_engine workaround): ROADMAP calls for live endpoint"
  - "Popularity threshold < 40 for related-artist candidates: mirrors existing strategy deep-cut definition"

patterns-established:
  - "Pattern: All ORM queries in HybridRecommendationEngine scoped to user=self.user (T-03-01 mitigation)"
  - "Pattern: Rate-limit gating per strategy call site AND per inner iteration loop"
  - "Pattern: per-strategy try/except + continue for graceful degradation without aborting pipeline"

requirements-completed:
  - exclusion-set
  - artist-filter
  - related-artists
  - reclog-exclusion

# Metrics
duration: 4min
completed: 2026-05-07
---

# Phase 1 Plan 3: Recommendation Engine Candidate Pipeline Fixes Summary

**DB-backed persistent exclusion set replaces batched Spotify API calls, removes top-artist name filter (Bug 5+6), and adds artist_related_artists as 5th candidate strategy (Bug 7)**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-07T20:41:06Z
- **Completed:** 2026-05-07T20:45:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `_get_persistent_exclusion_set()` — DB-backed set combining RecommendationLog (excluding 'error_log' sentinel) and DailyGem history; single SQL query pair instead of batched Spotify API calls
- Replaced `_filter_out_liked_songs()` body — no live API calls, no top-artist name filter, O(1) in-memory set membership check (Bug 5 + Bug 6 fix)
- Added `_get_related_artist_recommendations()` — 5th strategy using sp.artist_related_artists(), seeds from top 4 artists, pulls low-popularity (< 40) album cuts from 5 related artists per seed (Bug 7 fix)
- Wired Strategy 5 into get_recommendations() after Strategies 1-3 with rate-limit gate and limit * 2 over-fetch

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _get_persistent_exclusion_set and replace _filter_out_liked_songs** - `1051f5b7` (feat)
2. **Task 2: Add _get_related_artist_recommendations 5th strategy and wire into get_recommendations** - `73e4776e` (feat)

## Files Created/Modified
- `backend/apps/recommendations/hybrid_recommendation_engine.py` - Added `_get_persistent_exclusion_set()` helper, replaced `_filter_out_liked_songs()` body, added `_get_related_artist_recommendations()` strategy, wired Strategy 5 into `get_recommendations()`

## Decisions Made
- **DB exclusion set over live API calls:** `RecommendationLog` + `DailyGem` ORM queries are more reliable and don't burn rate limit budget at filter time; the existing real-time `saved_tracks_contains` check in `get_daily_gem` view is the correct last-gate (not the bulk filter)
- **Remove artist-name filter entirely:** The `top_artist_names` block was blocking discovery of deep cuts from familiar artists — the exact tracks a discovery engine should surface. Track-level ID exclusion via the DB set is the correct granularity.
- **Local imports inside _get_persistent_exclusion_set:** RecommendationLog and DailyGem imported locally to match Pattern 1 from PATTERNS.md and avoid circular import risk between recommendations and core apps.
- **artist_related_artists used directly (not via track_discovery_engine workaround):** ROADMAP calls for the live endpoint. If it soft-deprecates and returns empty, Strategy 5 produces 0 candidates but the pipeline still works with 4 other strategies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring referenced filtered strings causing grep false-positives**
- **Found during:** Task 1 verification
- **Issue:** The original docstring body for `_filter_out_liked_songs` contained the literal strings `top_artist_names` and `current_user_saved_tracks_contains` as reference text, causing acceptance criteria grep checks to return 1 instead of 0
- **Fix:** Rewrote docstring to describe the removed behavior without using the removed identifiers as literal strings
- **Files modified:** backend/apps/recommendations/hybrid_recommendation_engine.py
- **Verification:** Both greps now return 0
- **Committed in:** 1051f5b7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in docstring text)
**Impact on plan:** Minimal. Docstring text adjusted to pass acceptance criteria greps without changing any logic.

## Issues Encountered

**Plan acceptance criteria mismatch — views.py:**
The plan acceptance criterion states `grep -c 'current_user_saved_tracks_contains' backend/apps/core/views.py` should output at least 1 (the last-gate check RESEARCH describes at line ~1050 of get_daily_gem). Actual inspection of views.py shows no `current_user_saved_tracks_contains` call in the file (only `current_user_saved_tracks_add` and `current_user_saved_tracks` exist). This is a pre-existing absence — RESEARCH referenced the wrong method name or wrong line. Plan 03 does not touch views.py, per plan constraints, so this discrepancy is logged here and not fixed.

**Plan acceptance criteria mismatch — _get_genre_search_recommendations:**
The plan's Task 1-03-02 acceptance criterion requires `grep` for 4 strategy method definitions including `_get_genre_search_recommendations`, but this method does not exist in the codebase. The existing engine has 3 strategies (playlist, artist_network, contextual). The count of 4 cannot be achieved without adding a method not called for by the plan. The actual implementation adds the 5th strategy as specified; the grep criterion reflects incorrect assumptions about the pre-existing codebase state.

**No manual smoke test run (artist_related_artists endpoint status):**
The plan's verification section calls for a manual smoke test checking whether `artist_related_artists` returns non-empty results. This requires a logged-in user with a valid Spotify token. No such user was available during execution. RESEARCH Open Question 1 (whether the endpoint is soft-deprecated) remains unresolved — Strategy 5 includes graceful degradation (returns [] with a log message) if the endpoint returns empty.

## Known Stubs
None - all new methods are fully implemented with no placeholder logic.

## Threat Flags
None - no new trust boundaries introduced. All ORM queries are scoped to `user=self.user` (T-03-01). API response parsing uses `.get()` with defaults (T-03-05). Popularity missing defaults to 100 which excludes the track (fails closed, T-03-08).

## Next Phase Readiness
- `_get_persistent_exclusion_set()` and refactored `_filter_out_liked_songs()` are ready for Plan 02 and Phase 2 ML scoring work
- Strategy 5 feeds additional candidates into the pool that Phase 3 bandits will need for diversity
- Tests (TestPersistentExclusionSet, TestFilterOutLikedSongs, TestRelatedArtistStrategy from Plan 01-01) will turn GREEN once both worktrees are merged

---
*Phase: 01-fix-foundation*
*Completed: 2026-05-07*

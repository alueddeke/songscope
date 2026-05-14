# Phase 7: Backend Wiring - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire score data that `_score_recommendations` already computes into DB persistence and API responses. Four surfaces:

1. **Score persistence**: `DailyGem.score_breakdown`, `score_total`, `taste_vector_snapshot`, `explanation` written at creation in `get_daily_gem` (fresh branch)
2. **Cached branch fix**: All 3 cached return sites in `get_daily_gem` (lines ~1060, ~1123, ~1139) read `gem.score_breakdown` / `gem.explanation` from DB instead of returning `{}`
3. **was_saved wiring**: `add_track_to_liked` sets `DailyGem.was_saved = True` for today's gem after successful Spotify save
4. **Compound metric**: `get_recommendation_metrics` adds `compound_hit_rate` key to its response

Phase ends when all 4 API contracts are correct (populated scores, explanation text, was_saved persistence, compound_hit_rate in metrics). Frontend rendering is Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Explanation Text Format (_build_gem_explanation)

- **D-01:** Pure function signature: `_build_gem_explanation(breakdown: dict, track_name: str, artist_name: str, source: str) -> str` — no OpenAI, no external calls, deterministic from score components.
- **D-02:** **Dominant signal = genre_sim**: sentence is genre-forward with % exposed — e.g., `"Matches your indie rock taste — genre similarity: 82%, discovered via playlist mining"`. Exposes cosine similarity component directly (strong interview talking point).
- **D-03:** **Dominant signal = novelty**: discovery angle — e.g., `"A hidden gem — low popularity score makes it a genuine discovery, found via artist network"`. Frames novelty positively, not as a genre-miss.
- **D-04:** **Dominant signal = feedback_multiplier**: feedback-forward — e.g., `"You've liked [artist] before — that feedback boosted this pick, sourced from related artists"`. Closes the feedback loop visibly for the user.
- **D-05:** Source strategy is always appended (e.g., "via playlist mining", "via artist network", "via contextual discovery", "via related artists", "via fallback"). Provenance shows the 5-strategy engine at work — good for interviews.
- **D-06:** Dominant component = whichever of `genre_sim`, `novelty`, `feedback_multiplier` has the highest value in `breakdown`. If breakdown is empty or all zeros, fall back to a neutral sentence: `"Picked based on your listening patterns"`.

### was_saved Wiring

- **D-07:** After a successful `sp.current_user_saved_tracks_add([track_id])` call, find today's DailyGem for this user with a matching track spotify_id: `DailyGem.objects.filter(user=..., date=today, track__spotify_id=track_id).update(was_saved=True)`.
- **D-08:** If no matching DailyGem is found (user saved a non-gem track, or saved yesterday's gem), silent no-op — `was_saved` stays null. No error, no log. The Spotify save still returns 200.
- **D-09:** Failure to write `was_saved` must never 500 the save action — wrap in try/except, log at debug level if desired, return success response regardless.

### Score Persistence Location

- **D-10:** All 4 fields (`score_breakdown`, `score_total`, `explanation`, `taste_vector_snapshot`) written as `defaults={...}` inside `get_or_create` in `get_daily_gem` (single DB write). The view already has all data: `gem_data` (breakdown + total), `engine.profile.data.get('taste_vector', {})` (snapshot), and `_build_gem_explanation(...)` (explanation).
- **D-11:** Cached branch fix: replace `'score_breakdown': {}` with `'score_breakdown': gem.score_breakdown` and `'explanation': gem.explanation` at all 3 cached return sites (lines ~1060, ~1123). Read directly from the gem object — no extra DB round-trip needed.

### Compound Hit Rate

- **D-12:** Denominator = `DailyGem.objects.filter(user=...).count()` — all gems, nulls count as misses. Matches how `gem_acceptance_rate` is computed (consistent formula). Formula: `hits = gems where was_liked=True OR was_saved=True; rate = hits / total`.
- **D-13:** Add `compound_hit_rate` to the JSON response of `get_recommendation_metrics` alongside `gem_acceptance_rate` (line ~488 in views.py). Use 0.0 as default when total is 0.

### Claude's Discretion

- Exact helper function placement (`_build_gem_explanation` as module-level in `views.py` or in a utils module — follow existing patterns)
- Test class naming and organization (follow `TestDailyGemWasLikedSync` pattern)
- Genre name extraction from `score_breakdown` — if `genre_sim` is dominant but no genre name is available, use a neutral fallback like "your top genres"

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SCHEMA-02, §SCHEMA-03, §SCHEMA-04, §EXPLAIN-01, §EXPLAIN-02, §METRIC-02 — exact success criteria and field specs (locked)
- `.planning/ROADMAP.md` §Phase 7 — 4 success criteria that must be TRUE (fresh branch scores, cached branch reads, was_saved, compound_hit_rate)

### Core Code Surfaces
- `backend/apps/core/views.py` `get_daily_gem` (line 1026) — 3 return sites to fix; fresh branch is where get_or_create + score write goes
- `backend/apps/core/views.py` `add_track_to_liked` (line 831) — add was_saved update after line 843 (successful Spotify save)
- `backend/apps/core/views.py` `get_recommendation_metrics` (line 404) — add compound_hit_rate computation alongside gem_acceptance_rate (line ~424)
- `backend/apps/recommendations/hybrid_recommendation_engine.py` `_score_recommendations` (line 831) — already produces `score_breakdown` dict with `genre_sim`, `novelty`, `feedback_multiplier`; no changes needed here

### Model
- `backend/apps/core/models.py` class `DailyGem` — `score_breakdown` (JSONField, default=dict), `score_total` (FloatField, null/blank), `was_saved` (BooleanField, null/blank), `taste_vector_snapshot` (JSONField, null/blank), `explanation` (already exists) — all added in Phase 6 migration 0008

### Tests to Extend
- `backend/tests/test_feedback.py` — existing ORM patterns; `TestDailyGemWasLikedSync` (line 69) is the model test pattern
- `backend/tests/test_views_gem_feedback.py` — view-level test patterns; extend for compound_hit_rate and was_saved
- `backend/tests/test_recommendation.py` — get_daily_gem test patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_score_recommendations` already returns `rec['score_breakdown'] = {'genre_sim': ..., 'novelty': ..., 'feedback_multiplier': ...}` and `rec['score'] = ...` — no engine changes needed; view reads these from `candidates[0]`
- `gem.was_liked` / `gem.save(update_fields=['was_liked'])` pattern (lines 636, 693) — exact template for `was_saved` update in `add_track_to_liked`
- `gem_acceptance_rate` formula (line 424) — direct analog for `compound_hit_rate`; use same queryset pattern

### Established Patterns
- `DailyGem.objects.get_or_create(user=..., date=today, defaults={...})` — already in `get_daily_gem` line 1095; expand `defaults` dict to include 4 new fields
- `engine.profile.data.get('taste_vector', {})` — `HybridRecommendationEngine` stores `profile`; `profile.data` is the `UserProfile.data` JSONField where taste vector lives
- `try/except` non-fatal pattern already used in `was_liked` sync (submit_feedback view line 631–637) — follow same pattern for `was_saved`

### Integration Points
- `get_daily_gem` line 1082: `gem_data = candidates[0]` — `gem_data` has `score_breakdown` and `score` (= `score_total`) already
- Cached branch at line 1044–1062: `gem` object is fetched from DB; `gem.score_breakdown` and `gem.explanation` are readable immediately
- Race-condition branch at line 1106–1124: same — `gem` object is the race-winner from DB; read fields directly

</code_context>

<specifics>
## Specific Ideas

- Explanation sentence format examples (locked):
  - Genre dominant: `"Matches your [genre] taste — genre similarity: 82%, discovered via playlist mining"`
  - Novelty dominant: `"A hidden gem — low popularity score makes it a genuine discovery, found via artist network"`
  - Feedback dominant: `"You've liked [artist] before — that feedback boosted this pick, sourced from related artists"`
- `_build_gem_explanation` should handle missing genre gracefully — if `genre_sim` dominant but no genre available, use `"your listening taste"` as placeholder
- `compound_hit_rate` key must appear in metrics response even when 0 (don't omit it conditionally — frontend Phase 8 expects it)

</specifics>

<deferred>
## Deferred Ideas

- Backfilling `was_saved` for historical gems via Spotify saved-tracks API — out of scope; Phase 7 only captures going-forward saves
- Rolling window for `compound_hit_rate` (e.g., last 7 days) — deferred to Phase 8/evaluation dashboard
- Model-level `compound_hit` property on `DailyGem` — not needed for Phase 7; compute inline in the metrics view

</deferred>

---

*Phase: 07-backend-wiring*
*Context gathered: 2026-05-14*

# Phase 2: User Taste Vector & Real Scoring - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace static source weights with a real scoring function. Build a genre frequency vector from the user's top artists. Score candidate tracks by cosine similarity to that vector plus a novelty factor. Wire artist-level feedback signals into ranking. Add `source` field to `RecommendationLog` for per-strategy win-rate tracking. Remove dead AI audio-feature weight code.

Final score formula (locked by ROADMAP):
```
score = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier
```

</domain>

<decisions>
## Implementation Decisions

### Genre Frequency Vector

- **D-01:** Data source is `top_artists` only — already fetched in `_update_profile_data()`. No extra Spotify API calls.
- **D-02:** Weighting is flat count — each genre occurrence on each artist adds 1.0. No TF-IDF corpus needed.
- **D-03:** Stored as raw counts: `UserProfile.data['taste_vector'] = {"indie rock": 7, "folk": 4, ...}`. Not pre-normalized — cosine similarity normalizes at score time. Human-readable for Phase 4 visualization.
- **D-04:** Vector rebuilds inside `_update_profile_data()` alongside the top_artists fetch — same cadence as profile refresh. No separate rebuild logic.

### Scoring Function

- **D-05:** `genre_sim` = cosine similarity between the candidate track's artist genres (from `Track.genres` or live Spotipy call) and `UserProfile.data['taste_vector']`.
- **D-06:** `novelty` = `1 - (popularity / 100)`. Use the `popularity` field already present on recommendation dicts.
- **D-07:** `feedback_multiplier` = artist-level liked/disliked signal. Source: `UserProfile.data['preferences']['liked_artists']` and `disliked_artists`. Liked artist → positive bump; disliked artist → negative penalty. (Same artists referenced in current `_score_recommendations()` but now as a proper 0.3-weighted component instead of an ad hoc add-on.)

### AI Audio Feature Weights — Remove as Dead Code

- **D-08:** Delete `_update_weights_from_ai_feedback()` from `hybrid_recommendation_engine.py` (line ~898). The three keys `tempo_weight`, `energy_weight`, `valence_weight` are never readable from new tracks (Spotify audio_features endpoint gone) so updating them produces zero real effect.
- **D-09:** Remove `tempo_weight`, `energy_weight`, `valence_weight` from the `recommendation_weights` dict in `get_recommendation_weights()` / wherever they're initialized. The `add_ai_feedback()` pathway that calls `_update_weights_from_ai_feedback()` should stop calling it — the rest of `add_ai_feedback()` (storing AI feedback history) can remain.

### Per-Strategy Win-Rate Storage

- **D-10:** Add `source = CharField(max_length=50, choices=[...], blank=True, default='')` to `RecommendationLog` model. Requires one Django migration. Source values: `playlist_mining`, `artist_network`, `genre_search`, `related_artists`, `contextual`.
- **D-11:** Cold-start fallback: if a source has fewer than a minimum threshold of logged recommendations, fall back to the existing hardcoded static weights from `get_recommendation_weights()`. Planner decides the threshold (e.g., N=5). Win-rate replaces static weights only once there's enough data.

### Claude's Discretion

- Cold-start threshold N for per-strategy win-rate — planner chooses based on what makes the fallback feel smooth (suggested: 5 recommendations per source).
- Whether `Track.genres` is already populated in the DB for most candidates or needs a live `sp.artist()` lookup to get genres at score time — researcher should check.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` §Phase 2 — full deliverables list, formula, "why this order" rationale
- `.planning/PROJECT.md` §Context — Spotify API deprecations, ML approach, constraints, current engine state post-Phase 1

### Engine Files to Modify
- `backend/apps/recommendations/hybrid_recommendation_engine.py` — `_score_recommendations()` (line 717) is the primary function to replace; `_update_profile_data()` is where taste vector build hooks in; `_update_weights_from_ai_feedback()` (line 898) is to delete
- `backend/apps/recommendations/personalization_engine.py` — `_calculate_feature_preferences()` (currently returns defaults, audio features unavailable) — researcher should verify whether this is also dead code

### Data Model
- `backend/apps/core/models.py` — `RecommendationLog` (add `source` field + migration); `UserProfile` (`data` JSONField schema — `taste_vector` key to add alongside existing `cache`, `preferences`, `recommendation_weights`, `feedback_history`)

### Architecture
- `.planning/codebase/ARCHITECTURE.md` §Data Models — full model field list; §Recommendation Data Flow — where scoring fits in the request lifecycle

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UserProfile.data` JSONField (`backend/apps/core/models.py`) — already used as app-level cache and preference store. Add `taste_vector` key following the same pattern as `cache`, `preferences`, etc.
- `_update_profile_data()` in `hybrid_recommendation_engine.py` — already fetches `sp.current_user_top_artists()` and stores artist data in `base_data`. Genre arrays are on artist objects — just iterate and count.
- `liked_artists` / `disliked_artists` in `UserProfile.data['preferences']` — already populated by `add_feedback()`. feedback_multiplier reads these directly.

### Established Patterns
- Source weights: `_score_recommendations()` already reads `weights = self.profile.get_recommendation_weights()` and accesses `weights.get(rec['source'], 0.1)` — same pattern, extend with DB win-rate lookup before the static fallback.
- Recommendation dicts carry `source`, `popularity`, `artist`, `id` keys — all inputs to the new formula are already in the dict; no schema changes to recommendation dicts needed.

### Integration Points
- `_score_recommendations()` (line 717) — drop-in replacement: new function takes same input list, returns same sorted list with updated `score` values. No other code needs to change at the call sites.
- `RecommendationLog.log_recommendation()` call in `views.py` — needs to pass `source=rec['source']` once the field is added.
- `_update_profile_data()` — add taste vector build at the end of the existing top_artists processing block.

</code_context>

<specifics>
## Specific Ideas

- Taste vector key: `UserProfile.data['taste_vector']` (parallel to existing `UserProfile.data['cache']` and `UserProfile.data['preferences']`)
- Score formula weights match ROADMAP exactly: `0.4 / 0.3 / 0.3` — do not deviate
- Novelty formula matches ROADMAP exactly: `1 - (popularity / 100)` — do not deviate

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-user-taste-vector-real-scoring*
*Context gathered: 2026-05-07*

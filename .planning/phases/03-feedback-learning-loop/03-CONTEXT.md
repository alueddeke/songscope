# Phase 3: Feedback Learning Loop - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the recommendation engine learn from user feedback. Each like/dislike updates the genre taste vector online (no rebuild). A Thompson Sampling bandit tracks per-source success rates and replaces static source weights. Popularity targeting personalizes the novelty component via a bell-curve centered on the user's preferred popularity range. Gem explanations cite actual score components in the OpenAI prompt and return a score breakdown dict in the API response.

</domain>

<decisions>
## Implementation Decisions

### Taste Vector Online Update

- **D-01:** Update is **immediate and online** — on like/dislike, update `UserProfile.data['taste_vector'][genre]` in place and save to DB. No rebuild cycle needed. Hook lives in `PersonalizationEngine.apply_feedback_learning()` (currently a no-op).
- **D-02:** Learning rate `lr = 0.1` (conservative, stable SGD). Same lr for both like and dislike directions.
- **D-03:** Like → `taste_vector[genre] += 0.1` for each genre on the liked track's artist(s). Dislike → `taste_vector[genre] -= 0.1`. No floor — vector entries can go negative (active genre avoidance).
- **D-04:** Unlike (toggle off a previous like) → **reverse the update**: `taste_vector[genre] -= 0.1` for genres that were incremented. Use `feedback_history` entries (already stored in `UserProfile.data['preferences']['feedback_history']`) to retrieve the track's genres at undo time.
- **D-05:** Genres to update come from `track_info` dict already passed to `add_feedback()` — researcher should verify the `genres` key is populated on that dict at feedback time (it comes from `Track.genres` or a live `sp.artist()` call in `submit_feedback` view).

### Thompson Sampling Bandit

- **D-06:** **Success** = any positive feedback (LIKE or SAVE) on any recommended track — not limited to gems. Source gets credit whenever its track earns positive feedback. Derive from `RecommendationLog.source` + `UserFeedback.feedback_type` join.
- **D-07:** Bandit state stored as `UserProfile.data['source_stats']` — new JSON key alongside `taste_vector`. Schema: `{'playlist_mining': {'s': 0, 'f': 0}, 'artist_network': {'s': 0, 'f': 0}, 'genre_search': {'s': 0, 'f': 0}, 'related_artists': {'s': 0, 'f': 0}, 'contextual': {'s': 0, 'f': 0}}`. Updated at feedback time (no migration needed — JSONField).
- **D-08:** Integration point: **replace output of `get_recommendation_weights()`**. At recommendation time, sample `Beta(s+1, f+1)` for each source and use sampled values as weights. Existing `_score_recommendations()` already reads `weights[source]` — zero changes to scoring code, only `get_recommendation_weights()` changes.
- **D-09:** All 5 sources continue to run every cycle (no source skipping). Bandit influences relative weight, not which sources are called.

### Popularity Targeting (Personalized Novelty)

- **D-10:** Replace `novelty = 1 - (popularity / 100)` with a **bell-curve novelty** centered on `preferred_popularity_range['midpoint']`. Formula: Gaussian or triangular peak at midpoint, falling off symmetrically. Outer scoring coefficients (0.4/0.3/0.3) remain locked from Phase 2.
- **D-11:** Cold start: `preferred_popularity_range` initialized to `{'midpoint': 30, 'width': 20}` — biased toward low-popularity (hidden gem default). Stored in `UserProfile.data['preferences']['preferred_popularity_range']`.
- **D-12:** Like → `midpoint += 0.1 * (track_popularity - midpoint)` (same lr=0.1 pattern as taste vector). Dislike → `midpoint -= 0.1 * (track_popularity - midpoint)`. Unlike → reverse the like shift.

### "Why This Gem" Explanation

- **D-13:** Pass score breakdown (`genre_sim`, `novelty`, `feedback_multiplier` as floats, plus contributing genre names) into the `RecommendationExplainer` prompt context. GPT-4o-mini weaves them into natural language. One prompt change to `ai_feedback_service.py`.
- **D-14:** Also return score breakdown as structured data in the `/api/daily-gem/` response: `{"explanation": "...", "score_breakdown": {"genre_sim": 0.82, "novelty": 0.71, "feedback_multiplier": 1.5, "top_genres": ["indie rock", "folk"]}}`. Frontend can display or ignore for now. Good for Phase 4 visualization.

### Claude's Discretion

- Exact bell-curve formula for novelty (Gaussian vs triangular) — planner chooses based on simplicity. Triangular is ~3 lines; Gaussian needs `math.exp`.
- `width` parameter behavior on the popularity range — whether `width` is fixed or also updates over time.
- Cold-start threshold for bandit (how many `s+f` before bandit weights override the static defaults) — planner decides, suggest `N=3` per source before trusting the bandit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` §Phase 3 — full deliverables list, "why this order" rationale, concepts introduced
- `.planning/PROJECT.md` §Context and §Key Decisions — locked scoring formula, compound metric intent, constraint list
- `.planning/phases/02-user-taste-vector-real-scoring/02-CONTEXT.md` — all Phase 2 decisions (taste vector schema, scoring formula locked values, dead code removed)

### Engine Files to Modify
- `backend/apps/recommendations/hybrid_recommendation_engine.py`
  - `_score_recommendations()` (line 753) — novelty computation changes here (bell-curve replaces `1 - pop/100`)
  - `get_recommendation_weights()` — bandit sampling replaces static dict return
  - `add_feedback()` / `remove_feedback()` (line 876, 881) — trigger online taste vector + popularity range + bandit state updates
- `backend/apps/recommendations/personalization_engine.py`
  - `apply_feedback_learning()` (line 251) — currently a no-op; becomes the online taste vector + popularity update handler
  - `remove_feedback_learning()` (line 270) — currently a no-op; becomes the undo handler
- `backend/apps/ai/ai_feedback_service.py` — `RecommendationExplainer.generate_explanation()` — prompt augmented with score breakdown dict
- `backend/apps/core/views.py` — `/api/daily-gem/` response serialization to include `score_breakdown`

### Data Model
- `backend/apps/core/models.py`
  - `UserProfile.data` JSONField — new keys: `source_stats`, `preferences.preferred_popularity_range`
  - `UserProfile.get_recommendation_weights()` (line ~142) — replaced by bandit sampling output
  - `UserProfile.add_feedback()` (line 92) — already writes `feedback_history`; Phase 3 hooks in after this
  - `RecommendationLog` — `source` field (Phase 2) + `UserFeedback.feedback_type` join → bandit success/failure counts
- `backend/apps/recommendations/personalization_engine.py` lines 251–290 — no-op methods being activated

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UserProfile.data['preferences']['feedback_history']` — already stores per-track feedback with `track_id`, `feedback_type`, `track_info`. Phase 3 reads this to get genres at update time and to reverse updates on unlike.
- `UserProfile.data['preferences']['liked_artists']` / `disliked_artists` — already read by `_score_recommendations()` as artist-level signal; Phase 3 doesn't change this, just adds genre-level update alongside it.
- `UserProfile.update_weights()` and `get_recommendation_weights()` — existing persistence pattern; bandit replaces the static dict returned from `get_recommendation_weights()`.
- `RecommendationLog.source` (Phase 2) — ready to join against `UserFeedback` for bandit success counting.
- `numpy` is installed and imported in `hybrid_recommendation_engine.py` — available for `Beta(s+1, f+1)` sampling (`numpy.random.beta`).

### Established Patterns
- All new state goes into `UserProfile.data` as new JSON keys — no new models, no migrations. Pattern established across all prior phases.
- Online updates: read `self.profile.data`, mutate in place, `self.profile.save(update_fields=['data'])`. Same as `add_feedback()`.
- Score formula: `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier` — **LOCKED**. Only the novelty *computation* changes, not the weights.

### Integration Points
- `PersonalizationEngine.apply_feedback_learning(feedback)` — receives `UserFeedback` ORM object. Called from `views.py` on every LIKE/DISLIKE. This is where taste vector and popularity range updates hook in.
- `PersonalizationEngine.remove_feedback_learning(track_id)` — called on unlike from `views.py`. Undo logic goes here.
- `HybridRecommendationEngine.get_recommendation_weights()` — called inside `_score_recommendations()`. Bandit sampling replaces the static dict return.
- `/api/daily-gem/` response in `views.py` — extend the response dict with `score_breakdown` key.
- `RecommendationExplainer.generate_explanation()` in `ai_feedback_service.py` — add `score_breakdown` as a parameter to the prompt template.

</code_context>

<specifics>
## Specific Ideas

- `source_stats` cold-start: initialize all 5 sources to `{'s': 0, 'f': 0}` if key absent. Planner sets threshold N (suggest 3) before bandit weights override statics.
- Bell-curve novelty: planner picks Gaussian (`math.exp(-((pop - midpoint)**2) / (2 * width**2))`) or triangular (simpler). Both are fine for interview discussion.
- Taste vector update applies to **all genres on the track's artist(s)**, not just the primary genre. Same flat-count logic as `_build_taste_vector()`.
- Score breakdown in API response: `genre_sim`, `novelty`, `feedback_multiplier` as floats (0–1 range), plus `top_genres` (top-3 matching genres by taste vector weight).
- Popularity midpoint default `30` — aligns with "hidden gem" bias for low-popularity tracks.

</specifics>

<deferred>
## Deferred Ideas

- Collaborative filtering across users — no user base yet; explicitly out of scope in PROJECT.md.
- Audio feature weights revival (BPM, energy, valence) — Spotify endpoint still gone; only viable if external dataset (Million Song, Last.fm) provides features. Deferred to Phase 4 or beyond.
- Source skipping via bandit (calling only top-N sources per cycle to save Spotify API calls) — decided to keep all 5 sources running; revisit if API rate limits become an issue.

</deferred>

---

*Phase: 03-feedback-learning-loop*
*Context gathered: 2026-05-11*

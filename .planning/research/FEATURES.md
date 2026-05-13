# Feature Landscape: Recommendation Explainability + Compound Success Metric

**Domain:** Music discovery app — adding explainability and outcome measurement to an existing ML recommendation system
**Researched:** 2026-05-13
**Scope:** v1.1 milestone — "Why This Gem" UX + compound success metric + per-recommendation outcome logging

---

## Context: What Already Exists

The scoring engine already computes and returns `score_breakdown` per recommendation:

```python
rec['score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),    # 0.0–1.0 cosine similarity
    'novelty': round(novelty, 4),         # 0.0–1.0 Gaussian bell-curve
    'feedback_multiplier': round(feedback_multiplier, 4),  # 0.5 / 1.0 / 1.5
    'source': rec.get('source', ''),      # which of 5 strategies found this
}
```

The `get_daily_gem` view passes `score_breakdown` through in the fresh-generation branch but returns `{}` for cached gems. `DailyGem.explanation` is persisted as a text field (already used by `RecommendationExplainer` via OpenAI). The new work is: render the breakdown in the UI, define a compound success metric, and log the right outcome fields.

---

## Table Stakes

Features users expect. Missing = portfolio project feels incomplete or ML claims are unverifiable.

| Feature | Why Expected | Complexity | Dependency on Existing Code |
|---------|--------------|------------|----------------------------|
| Score component display | Any ML app claiming explainability must show at minimum what factors drove the pick | Low | `score_breakdown` already returned by API fresh branch; needs cache-branch fix + frontend render |
| Human-readable genre reason | "Because you like indie rock" is what Spotify/Netflix style explanations set as the baseline expectation | Low | `taste_vector` already in `UserProfile.data`; top genre is `max(taste_vector)` |
| Novelty/popularity rationale | Users need to understand why a low-popularity track was surfaced — otherwise "gem" framing makes no sense | Low | `novelty` score + `track.popularity` already available |
| Score persisted at recommendation time | Without persisting the score components, offline evaluation is impossible; this is a data quality blocker | Low | `DailyGem` and `RecommendationLog` both lack score fields — requires migration |
| Binary outcome label (hit/miss) | The compound success metric (the explicit ML claim in the portfolio) requires a ground truth label | Low | `DailyGem.was_liked` exists; `was_saved` (Spotify library add) does not — see anti-features note |

---

## Differentiators

Features that make the portfolio stand out. Not expected, but signal ML depth.

| Feature | Value Proposition | Complexity | Dependency |
|---------|-------------------|------------|-----------|
| Dynamic explanation text tied to dominant score component | Instead of static "because you like X genre", the sentence adapts to whichever component was highest — genre_sim, novelty, or feedback_multiplier | Low–Med | Requires logic: if genre_sim > 0.7, template A; if novelty dominant, template B; no extra API call |
| Score component bar chart in gem card | Visual breakdown (three bars: genre match %, novelty %, feedback signal %) is a stronger portfolio artifact than text alone; research confirms hybrid text+visual builds more user trust than either alone | Med | Needs frontend component; data already available in `score_breakdown` |
| Source attribution in explanation | "Found via artist network" or "Discovered through your playlists" adds transparency to the Thompson Sampling strategy — shows the bandit is real | Low | `source` already in `score_breakdown` |
| Per-recommendation outcome logging (event log) | Enables future offline evaluation: precision@1, hit rate trend, per-source win rates; this is the dataset for the "evaluation dashboard" milestone | Med | Requires new `GemOutcome` model or extension of `DailyGem` with score fields + `was_saved` flag |
| Improvement trend tied to compound metric | "Your taste match has improved X% over the last 14 gems" gives a narrative around ML learning; stronger interview story than raw numbers | Med | Builds on existing `improvement_story` in `/api/recommendation-metrics/` — just needs compound metric as the signal |

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Percentage breakdowns with decimal precision (e.g., "73.4% genre match") | Research on recommendation explainability consistently shows users find simple/conclusive explanations more trustworthy than technical detail; decimals signal algorithmic output rather than human-friendly reasoning | Round to nearest 5% or use Low/Medium/High labels for display; keep precise values in the DB for ML use |
| Real-time "played" detection via Spotify API | `sp.current_user_recently_played` is a 50-item cursor, not a playback event webhook; matching a specific preview play to a specific gem recommendation is unreliable and adds significant complexity | Use Spotify library save (`sp.current_user_saved_tracks_contains()`) as the "saved" signal — this is already called in `get_daily_gem` for exclusion filtering |
| `preview_url` played duration tracking | Spotify deprecated `preview_url` for many tracks as of Nov 2024; the field returns null for a growing percentage of tracks; building UX around it creates fragile behavior | Log a boolean `preview_clicked` client-side if the user taps play, treat it as a weak signal only |
| "Open in Spotify" click tracking as a success signal | Click-through is a notoriously weak proxy — it can indicate curiosity or confusion, not genuine enjoyment; multiple studies confirm saves and explicit likes are stronger signals | Use thumbs-up (existing LIKE feedback) + Spotify library save as the compound metric |
| Confidence intervals or model uncertainty display | Academically interesting but over-engineers for a single-user portfolio app with ~30 data points; this needs hundreds of data points to be meaningful | Defer to future milestone when enough gems exist |
| A/B explanation format testing | No user base to test against; would require multi-user infrastructure | Hardcode the single best explanation format (natural language + source tag + optional bar chart); revisit if app goes multi-user |
| Retroactively explaining cached gems with new score | When a gem is returned from cache, `score_breakdown: {}` is intentional — re-scoring changes the explanation mid-day and confuses the user | Accept that cached gems show explanations without score components, or persist the breakdown at creation time (preferred) |

---

## Feature Dependencies

```
score_breakdown in API (exists, fresh branch only)
  → Fix: persist score_breakdown to DailyGem at creation
  → Enables: cache branch returns real breakdown
  → Enables: "Why This Gem" UI component (score bars + text)
  → Enables: per-recommendation outcome row with score fields

taste_vector in UserProfile.data (exists)
  → Enables: dynamic explanation text (top genre lookup)
  → Enables: "genre match" human-readable phrase

LIKE feedback (exists: UserFeedback + DailyGem.was_liked)
  → Enables: half of compound metric (liked = True)

Spotify library save check (exists: sp.current_user_saved_tracks_contains())
  → Enables: other half of compound metric (was_saved = True)
  → Requires: new DailyGem.was_saved BooleanField + periodic check endpoint

per-recommendation outcome log (new: DailyGem score fields + was_saved)
  → Enables: offline evaluation dataset
  → Enables: per-source win rate analysis (future eval dashboard)
  → Enables: compound success metric time series
```

---

## Explanation Format Recommendation

**Use: Natural language anchor + source tag + optional visual component**

Research evidence:
- Item-KNN and content-based systems most commonly use "Because you like [artist/genre]" style explanations; users find these simple and trustworthy (Wiley AI Magazine, 2022, "Explainability in music recommender systems")
- The most appealing explanations were simple/conclusive — "neighbors liked it", "similar to what you play" — while technical algorithmic representations scored lower on user satisfaction (ACM RecSys 2024 comparative analysis)
- Text + visual hybrid explanations build higher trust than either alone; a bar chart showing relative component weight is the simplest visual that adds value without overwhelming
- "Because you like X" outperforms percentage breakdowns for comprehension, but the percentage-style bar chart still has value as a secondary detail (expandable or dimmed by default)

**Recommended copy template logic:**

```
dominant_component = max(genre_sim * 0.4, novelty * 0.3, feedback_multiplier * 0.3)

if genre_sim is dominant and genre_sim > 0.5:
    "Matches your taste in [top_genre]"

elif novelty is dominant or popularity < 35:
    "A hidden gem — popularity [popularity], outside the mainstream"

elif feedback_multiplier == 1.5:
    "From an artist you've liked before"

fallback:
    "Picked for you based on your listening patterns"

append: "Found via [source_human_readable]"
    # playlist_mining   → "your playlists"
    # artist_network    → "artist connections"
    # related_artists   → "artists similar to your favorites"
    # genre_search      → "genre exploration"
    # contextual        → "your listening context"
```

This is deterministic, requires zero OpenAI calls, and is directly tied to the actual score formula — satisfying the PROJECT.md requirement "explanation text tied to actual score components, not canned copy."

The existing `RecommendationExplainer` OpenAI path can co-exist as a longer-form explanation below the component breakdown, but it should not be the primary explanation since it adds latency and cost.

---

## Compound Success Metric Definition

**Definition:** A gem is a "hit" when `was_liked = True` OR `was_saved = True` (Spotify library).

**Rationale:**
- Play data is unavailable — Spotify deprecated the playback state API for third-party apps; `recently_played` cursor is not a reliable event stream
- The 30-second Spotify stream threshold (the industry definition of a "play") cannot be observed via the Web API for third-party apps
- Library save is the strongest observable positive signal in music recommendation research — saves are 3x more likely from engaged listeners, and Spotify itself weights saves heavily in its own ranking
- LIKE (thumbs up in-app) is an explicit, deliberate signal; it already drives the taste vector update, making it the cleanest ground truth available
- OR logic (not AND) is correct for a single daily recommendation: requiring both save AND like in one day creates a very sparse label; OR captures genuine discovery better

**What this is NOT:**
- Not a "played" metric (unavailable)
- Not a "streamed past 30 seconds" metric (unavailable)
- Not "opened in Spotify" click-through (weak signal)

**Interview framing:**
> "Without playback state, I define a hit as the user performing at least one high-intent action: an in-app thumbs-up that updates their taste vector, or a Spotify library save. Both actions require deliberate intent. I log both per recommendation and compute a daily hit rate. This gives me a ground truth label I can use to evaluate the scoring formula — if genre_sim is the dominant component and hit rate is high, the cosine similarity is working."

---

## Per-Recommendation Outcome Logging

### Fields Worth Persisting (on DailyGem or new GemOutcome model)

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `score_at_recommendation` | FloatField | `rec['score']` at gem creation | Offline ranking evaluation; correlate score with outcome |
| `genre_sim_at_recommendation` | FloatField | `score_breakdown['genre_sim']` | Isolate whether genre component predicts hits |
| `novelty_at_recommendation` | FloatField | `score_breakdown['novelty']` | Isolate whether novelty component predicts hits |
| `feedback_multiplier_at_recommendation` | FloatField | `score_breakdown['feedback_multiplier']` | Isolate whether artist preference predicts hits |
| `source_at_recommendation` | CharField | `score_breakdown['source']` | Already exists on `RecommendationLog`; should also be on `DailyGem` |
| `was_liked` | BooleanField null | Existing `DailyGem.was_liked` | Already exists; half of compound metric |
| `was_saved` | BooleanField null | `sp.current_user_saved_tracks_contains()` | New field; other half of compound metric |
| `preview_clicked` | BooleanField default False | Frontend event, POST to new endpoint | Weak signal; worth capturing, not worth over-weighting |
| `taste_vector_snapshot` | JSONField | `UserProfile.data['taste_vector']` at gem creation | Reconstructs model state for any given day; critical for longitudinal analysis |

### What to NOT persist per-recommendation:
- Raw Spotify API response blobs — too large, changes too fast, not queryable
- Thompson Sampling Beta parameters snapshot — too granular; source_at_recommendation is sufficient
- User's full preference history — already in `UserProfile.data`; don't duplicate

### Implementation path (minimal migration):

**Option A — Extend DailyGem (simpler):**
Add `score_at_recommendation`, `genre_sim_at_recommendation`, `novelty_at_recommendation`, `feedback_multiplier_at_recommendation`, `source_at_recommendation`, `was_saved` to `DailyGem`. Migration is straightforward; all nullable with defaults.

**Option B — New GemOutcome model:**
Separate `DailyGem` (the daily pick) from `GemOutcome` (what happened after). Cleaner separation of concerns; better for future A/B testing. Adds complexity now.

**Recommendation:** Option A for this milestone. The app is single-user, single gem per day. Add a `GemOutcome` model when the evaluation dashboard milestone starts.

---

## MVP Recommendation for This Milestone

Build in this order:

1. **Persist score_breakdown to DailyGem** — add four nullable FloatFields + `source_at_recommendation`. Fixes the cache-branch `score_breakdown: {}` gap. One migration.

2. **"Why This Gem" UI** — render the explanation text (template-based, no OpenAI call) + source tag below the gem card. The bar chart visual is a differentiator; build it if time allows, otherwise text-only is the MVP.

3. **Add `was_saved` field to DailyGem + check endpoint** — a GET endpoint that calls `sp.current_user_saved_tracks_contains([gem.track.spotify_id])` and writes `gem.was_saved`. Call it on page load when a gem is displayed. This completes the compound metric.

4. **Compound metric in metrics strip** — add `hit_rate = (was_liked OR was_saved) / total_gems` as a new metric. Update `/api/recommendation-metrics/` response.

**Defer:**
- Score component bar chart visual (implement after text explanation is stable)
- `taste_vector_snapshot` (useful but not blocking; add in evaluation dashboard phase)
- `preview_clicked` logging (Spotify deprecated many `preview_url` fields; defer until scope is clear)

---

## Complexity Notes

| Feature | Estimate | Notes |
|---------|----------|-------|
| Persist score fields to DailyGem | Low | 1 migration, 5 new nullable columns; write at gem creation in `get_daily_gem` view |
| Template-based explanation text | Low | Pure Python logic in the view or a helper; no new dependencies |
| Source tag human-readable mapping | Low | Dict lookup; already have the source values |
| `was_saved` field + check endpoint | Low–Med | New endpoint; calls Spotify API once per page load; rate limit aware |
| Score component bar chart (frontend) | Med | New React component; 3 proportional bars; no backend changes if score fields are persisted |
| Compound hit_rate metric | Low | Add to existing `get_recommendation_metrics` view; no new DB queries beyond what exists |
| `taste_vector_snapshot` at creation | Low | JSONField copy at DailyGem creation; ~2 lines |

---

## Sources

- "Explainability in music recommender systems" — Afchar, 2022. Wiley AI Magazine. https://onlinelibrary.wiley.com/doi/full/10.1002/aaai.12056
- "A Comparative Analysis of Text-Based Explainable Recommender Systems" — ACM RecSys 2024. https://dl.acm.org/doi/10.1145/3640457.3688069
- "Visualization for Recommendation Explainability: A Survey and New Perspectives" — ACM Transactions on Interactive Intelligent Systems. https://dl.acm.org/doi/10.1145/3672276
- "EXPLORE - Explainable Song Recommendation" — arXiv 2024. https://arxiv.org/html/2401.00353
- "Inside Spotify's Recommendation System: A Complete Guide" — music-tomorrow.com. https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide
- "The 30-Second Rule: Fix Your Spotify Skip Rate" — Chartlex. https://www.chartlex.com/blog/streaming/30-second-rule-spotify-intro-skip-rate
- "30s Preview_Url Deprecated" — Spotify Community, Nov 2024. https://community.spotify.com/t5/Spotify-for-Developers/30s-Preview-Url-Depriciated/td-p/6636451
- "Characterisation of explicit feedback in an online music recommendation service" — ACM RecSys 2010. https://dl.acm.org/doi/10.1145/1864708.1864776
- "Leveraging Negative Signals with Self-Attention for Sequential Music Recommendation" — arXiv 2023. https://arxiv.org/html/2309.11623
- "10 metrics to evaluate recommender and ranking systems" — EvidentlyAI. https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems

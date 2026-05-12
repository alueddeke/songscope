# Phase 4: Metrics, Evaluation & Documentation - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the loop on the working ML system. Implement the `/api/recommendation-metrics/` and `/api/recommendation-trend/` backend endpoints (all metrics computed on-the-fly from existing data — no new DB columns). Add Recharts-powered visualizations at the bottom of the profile page: a 7-day like-rate trend chart and a taste profile genre bar chart. Produce interview-ready documentation: `CONCEPTS.md` (ML/DS algorithms with intuition + formula + code snippet) and `SYSTEM_DESIGN.md` (Mermaid architecture diagram + component descriptions) at repo root, complementing the existing `INTERVIEW_PREP_SONGSCOPE.md`.

</domain>

<decisions>
## Implementation Decisions

### Metrics Persistence Strategy

- **D-01:** All metrics are computed on-the-fly from existing `RecommendationLog` and `DailyGem` rows — no new DB columns, no new migrations needed.
- **D-02:** Implement `/api/recommendation-metrics/` to match the existing `MetricsStrip` component interface exactly: `{gem_total, gem_liked, gem_disliked, gem_acceptance_rate, avg_popularity, hidden_gem_rate, top_genres}`. MetricsStrip is already wired to this endpoint.
- **D-03:** Trend chart data lives in a separate `/api/recommendation-trend/` endpoint — clean separation from the strip metrics.
- **D-04:** "Feedback improvement story" compares **first 7 gems vs most recent 7 gems** by like-rate. Tells the learning curve story: "When I started: X% acceptance → Now: Y%."

### Chart Library & Visualization Placement

- **D-05:** Install **Recharts** as a new frontend dependency. Used for both the 7-day like-rate trend (line chart) and taste profile genre bar chart.
- **D-06:** New visualizations live in a **new section at the bottom of the profile page** (below TopArtists). Keeps the gem hero area clean; charts accessible by scrolling.
- **D-07:** Taste profile chart shows **top 10 genres, normalized to percentage** (genre_count / total_counts × 100). Horizontal bar chart — easier to read genre names than vertical.
- **D-08:** Trend chart shows rolling **7-day like-rate** (% of gems liked within a 7-day rolling window). Line chart with date on x-axis, like-rate (0–100%) on y-axis.

### Diversity Score Definition

- **D-09:** Diversity window = **all-time** (all DailyGem records for the user, not a rolling window). Captures total genre spread since first use.
- **D-10:** Genre distance between two recommendations = **Jaccard distance**: `1 - |A ∩ B| / |A ∪ B|` where A and B are the genre sets of each track's artist(s). Two tracks with no genres in common = 1.0 (fully diverse). Identical genres = 0.0.
- **D-11:** Final diversity scalar = **mean pairwise Jaccard distance** across all N*(N-1)/2 pairs of all-time recommended gems. Single interpretable number.

### Documentation Scope & Format

- **D-12:** `CONCEPTS.md` and `SYSTEM_DESIGN.md` are **new docs at repo root**, complementing (not replacing) `INTERVIEW_PREP_SONGSCOPE.md`. Three docs coexist.
- **D-13:** `SYSTEM_DESIGN.md` contains a **Mermaid diagram** (renders natively on GitHub) showing data flow: Spotify API → candidate strategies → scoring → feedback loop → taste vector update → bandit update.
- **D-14:** `CONCEPTS.md` covers every ML/DS algorithm at depth **intuition + formula + code snippet** level. Covers: cosine similarity, novelty scoring, Thompson Sampling, online learning (SGD taste vector), Jaccard diversity, recommendation evaluation metrics (precision@k, serendipity, diversity, coverage), the compound success metric.
- **D-15:** `CONCEPTS.md` also includes: why each design decision was made (API constraints, portfolio rationale), mathematical formulations, and interview talking points for each concept.

### Claude's Discretion

- Exact Recharts component API choices (BarChart vs custom wrappers, color theme — should match existing green accent from MetricsStrip's `text-green` class).
- Whether `/api/recommendation-trend/` returns daily or per-gem data points.
- Cold-start handling when fewer than 7 gems exist (show what's available vs return empty).
- Whether diversity score appears in MetricsStrip (extending existing interface) or only in the new bottom section.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` §Phase 4 — full deliverables list, concepts introduced, dependency order
- `.planning/PROJECT.md` §Core Value, §Constraints, §Key Decisions — interview-readiness requirement, single-user constraint, ML approach decisions
- `.planning/phases/03-feedback-learning-loop/03-CONTEXT.md` — Phase 3 decisions (taste vector schema, bandit state, score_breakdown API response structure, bell-curve novelty)
- `.planning/phases/02-user-taste-vector-real-scoring/02-CONTEXT.md` — scoring formula (LOCKED: 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier), taste_vector schema

### Frontend Components to Extend or Wire
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — already built, calls `/api/recommendation-metrics/`, interface is LOCKED (D-02 matches exactly)
- `frontend/app/profile/page.tsx` — add new bottom section with Recharts components below TopArtists
- `frontend/services/axios.ts` — use existing `get()` helper for all new API calls

### Backend Files to Modify
- `backend/apps/core/views.py` — add `get_recommendation_metrics()` view and `get_recommendation_trend()` view
- `backend/config/urls.py` — register `/api/recommendation-metrics/` and `/api/recommendation-trend/`
- `backend/apps/core/models.py` — `RecommendationLog` (liked, was_novel, track_popularity, source), `DailyGem` (was_liked, track_popularity, date, track) — data sources for all metrics

### Data Model Fields Available for Metrics (no new columns needed)
- `DailyGem.was_liked` + `DailyGem.date` + `DailyGem.track_popularity` → like_rate, trend, acceptance rate
- `RecommendationLog.was_novel` → hidden_gem_rate, novel_track_rate
- `UserProfile.data['taste_vector']` → top_genres, genre bar chart data
- `Track.genres` (via DailyGem.track FK → Track.genres) → diversity Jaccard computation

### Existing Interview Doc
- `INTERVIEW_PREP_SONGSCOPE.md` (repo root) — 842 lines, Phase 1-era content; CONCEPTS.md complements and updates it with Phases 2-4 concepts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MetricsStrip.tsx` — already implements the metrics strip UI; `/api/recommendation-metrics/` just needs the backend implementation to match its interface
- `frontend/services/axios.ts` `get()` helper — used for all API calls from frontend components; use for trend + taste profile endpoints
- `UserProfile.data['taste_vector']` — already populated by Phase 2; top 10 genres normalized is a simple sort + slice + normalize on this dict
- `UserProfile.data['source_stats']` (Phase 3) — bandit state available if metrics need per-source stats
- `DailyGem` queryset — `DailyGem.objects.filter(user=user).order_by('date')` gives chronological gem history for trend and diversity computation

### Established Patterns
- All views in `backend/apps/core/views.py` — register new views here, add URL in `backend/config/urls.py`
- All new frontend components under `frontend/app/profile/components/<ComponentName>/<ComponentName>.tsx` with `"use client"` directive
- `UserProfile.data` JSONField for all user state — `taste_vector` is the data source; no new model fields
- Color theme: `text-green` (existing MetricsStrip accent color) — Recharts charts should use the same green for consistency

### Integration Points
- `/api/daily-gem/` response now includes `score_breakdown: {genre_sim, novelty, feedback_multiplier, top_genres}` (Phase 3) — CONCEPTS.md should document this
- `RecommendationLog` has `source` field (Phase 2) — available for per-source metrics if added to metrics endpoint
- Track.genres field — key for diversity computation; researcher should verify it's populated for DailyGem tracks (or needs artist lookup at compute time)

</code_context>

<specifics>
## Specific Ideas

- `hidden_gem_rate` in MetricsStrip = tracks with popularity < 40 (or `was_novel=True` from RecommendationLog) — researcher should check which field is more reliable
- Recharts color: match existing `text-green` accent (`#22c55e` or whatever Tailwind green is configured as) — check `tailwind.config.ts` for exact value
- Diversity score display: surface in the new bottom section alongside the charts (not in MetricsStrip, to avoid changing the existing interface)
- CONCEPTS.md should explicitly cover the "Spotify API deprecation pivot" story — it's a strong interview talking point (D-15 rationale)
- First 7 vs last 7 before/after comparison: if fewer than 7 gems exist, compare first half vs second half, or skip if < 2 gems

</specifics>

<deferred>
## Deferred Ideas

- Security hardening (SECRET_KEY rotation, CSRF re-enable, Spotify client secret removal from browser bundle) — explicitly out of scope per PROJECT.md, deferred to post-ML milestone
- Collaborative filtering metrics (coverage across hypothetical user base) — no user base yet
- Audio feature weights revival (BPM, energy, valence via external dataset) — deferred from Phase 3, still deferred
- A/B testing infrastructure — ROADMAP introduces the concept but implementing actual A/B tests is out of Phase 4 scope

</deferred>

---

*Phase: 04-metrics-evaluation-documentation*
*Context gathered: 2026-05-11*

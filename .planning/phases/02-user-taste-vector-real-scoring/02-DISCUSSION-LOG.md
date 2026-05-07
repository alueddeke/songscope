# Phase 2: User Taste Vector & Real Scoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 02-user-taste-vector-real-scoring
**Areas discussed:** Genre data depth, AI weight disposition, Taste vector rebuild cadence, Per-strategy win-rate storage

---

## Genre Data Depth

| Option | Description | Selected |
|--------|-------------|----------|
| top_artists only | Already fetched in _update_profile_data(). Zero extra API calls. | ✓ |
| top_artists + saved track artists | Richer signal but 3-5 extra API calls per profile refresh. | |
| top_artists + recently_played artists | Captures recency bias; artists need sp.artists() for genre arrays. | |

**User's choice:** top_artists only

### Follow-up: Genre frequency weighting

| Option | Description | Selected |
|--------|-------------|----------|
| Flat count | Each genre occurrence = 1.0. Simple, interpretable. | ✓ |
| TF-IDF style | Weight rare genres higher. Requires genre corpus for IDF. | |
| Artist popularity-weighted | More popular artists contribute more. Wrong signal for discovery. | |

**User's choice:** Flat count

---

## AI Weight Disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Remove as dead code | Delete _update_weights_from_ai_feedback() and three weight keys. | ✓ |
| Fold into feedback_multiplier | Map AI sentiment to ±0.1 multiplier. Arbitrary without audio features. | |
| Preserve but don't apply | Keep storage/update logic, never read weights in scoring. | |

**User's choice:** Remove as dead code

### Follow-up: feedback_multiplier replacement

| Option | Description | Selected |
|--------|-------------|----------|
| Artist-level liked/disliked signal | Reads liked_artists/disliked_artists already in UserProfile.data. | ✓ |
| RecommendationLog like-rate per source | Depends on per-strategy win-rate data. | |
| Composite: artist signal + source win-rate | More signals but more complexity and sparsity risk. | |

**User's choice:** Artist-level liked/disliked signal

---

## Taste Vector Rebuild Cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Piggyback on profile update | Rebuild inside _update_profile_data() alongside top_artists fetch. | ✓ |
| Lazy: build once, never auto-rebuild | Only rebuild on force_fresh=True. Vector goes stale. | |
| Triggered by feedback | Full top_artists fetch on every like/dislike. Expensive. | |

**User's choice:** Piggyback on profile update

### Follow-up: Vector key structure

| Option | Description | Selected |
|--------|-------------|----------|
| Raw counts: {"indie rock": 7, ...} | Human-readable, normalizes at score time. | ✓ |
| Pre-normalized: {"indie rock": 0.58, ...} | Marginal perf gain, less interpretable. | |
| You decide | Researcher/planner chooses based on codebase patterns. | |

**User's choice:** Raw counts

---

## Per-Strategy Win-Rate Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Add source field to RecommendationLog | One migration, SQL-queryable win-rates. | ✓ |
| Track in UserProfile.data JSON | No migration but harder to query, divergence risk. | |
| Deferred to Phase 3 | Phase 3 is where win-rates get consumed by Thompson Sampling. | |

**User's choice:** Add source field to RecommendationLog

### Follow-up: Cold-start behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current hardcoded weights as fallback | Smooth transition — real data wins once data accumulates. | ✓ |
| Equal weights for all sources | Flat 0.2 per source. Removes existing genre_search bias. | |
| You decide | Planner chooses cold-start threshold and fallback weights. | |

**User's choice:** Keep current hardcoded weights as fallback

---

## Claude's Discretion

- Cold-start threshold N for per-strategy win-rate (suggested: 5 recommendations per source)
- Whether `Track.genres` is populated in DB for most candidates or needs live sp.artist() lookup at score time

## Deferred Ideas

None — discussion stayed within phase scope.

# Phase 3: Feedback Learning Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 03-feedback-learning-loop
**Areas discussed:** Taste Vector Update, Bandit Integration, Popularity Targeting, "Why This Gem" Explanation

---

## Taste Vector Update

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate online update | Update taste_vector in place on like/dislike, save to DB, next rec uses updated vector | ✓ |
| Batch on next rebuild | Accumulate signals, apply on next _build_taste_vector() call | |
| You decide | Planner/researcher chooses | |

**User's choice:** Immediate online update

| Option | Description | Selected |
|--------|-------------|----------|
| lr=0.1 conservative | Small step per feedback, stable SGD | ✓ |
| lr=0.3 moderate | Faster adaptation, riskier on accidental feedback | |
| Adaptive decay | lr = base_lr / sqrt(1 + n_feedback), more principled | |

**User's choice:** lr=0.1

| Option | Description | Selected |
|--------|-------------|----------|
| Subtract (can go negative) | Symmetric SGD, dislike = active genre avoidance | ✓ |
| Clamp to zero | Never negative, reduces affinity only | |
| You decide | Planner picks | |

**User's choice:** Subtract (vector[genre] -= 0.1, no floor)

| Option | Description | Selected |
|--------|-------------|----------|
| Reverse the update | Subtract what was added on unlike | ✓ |
| No-op (leave vector) | Signal was valid at time, don't undo | |
| You decide | Planner decides | |

**User's choice:** Reverse the update (undo the like's increment)

---

## Bandit Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Gem liked only | Success = LIKE feedback on DailyGem. Compound signal, less data. | |
| Any positive feedback | Success = LIKE or SAVE on any recommended track. More data, slightly noisier. | ✓ |
| You decide | Planner defines success | |

**User's choice:** Any positive feedback (LIKE or SAVE) on any recommended track

| Option | Description | Selected |
|--------|-------------|----------|
| UserProfile.data['source_stats'] | New JSON key, no migration, updated at feedback time | ✓ |
| Compute from DB at decision time | Query RecommendationLog + UserFeedback join each request | |
| New SourceStats model | Explicit DB table with migration | |

**User's choice:** UserProfile.data['source_stats']

| Option | Description | Selected |
|--------|-------------|----------|
| Replace get_recommendation_weights() output | Bandit samples Beta(s+1,f+1), returns as weights dict. Zero scoring changes. | ✓ |
| Probabilistic source selection | Bandit picks which sources to call, reduces API calls | |
| Post-hoc score multiplier | All sources run, bandit multiplies final score | |

**User's choice:** Replace get_recommendation_weights() output

---

## Popularity Targeting

**Notes:** User initially asked why option 2 was not recommended. Clarification: the Phase 2 lock was on the formula *weights* (0.4/0.3/0.3), not on how novelty is computed. Changing novelty from `1 - pop/100` to a bell-curve changes the computation without changing the coefficients. User agreed this is valid and more effective.

| Option | Description | Selected |
|--------|-------------|----------|
| Bell-curve novelty centered on preferred range | Outer weights unchanged. Novelty personalizes via Gaussian/triangular peak. | ✓ |
| Metadata only, no scoring change | Store range for explanation/interviews, keep 1 - pop/100 unchanged | |
| Skip (defer to Phase 4) | Conflicts with locked novelty formula | |

**User's choice:** Bell-curve novelty centered on preferred range

| Option | Description | Selected |
|--------|-------------|----------|
| Shift midpoint toward liked popularity (lr=0.1) | midpoint += 0.1 * (track_pop - midpoint). Same online-learning pattern as taste vector. | ✓ |
| Expand range to include liked popularity | min/max grow. Can get too wide. | |
| You decide | Planner chooses | |

**User's choice:** Shift midpoint toward liked track's popularity (lr=0.1)

---

## "Why This Gem" Explanation

| Option | Description | Selected |
|--------|-------------|----------|
| Augment OpenAI prompt with score data | Pass genre_sim, novelty, feedback_multiplier into prompt. GPT-4o-mini weaves them into text. | ✓ |
| Template-based, no AI | Generate explanation from scores directly. No cost, fully deterministic. | |
| Score breakdown alongside AI explanation | Keep AI prompt as-is, add breakdown dict to API response separately | |

**User's choice:** Augment OpenAI prompt with score data

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — return score dict in API response | {score_breakdown: {genre_sim, novelty, feedback_multiplier, top_genres}} in /api/daily-gem/ | ✓ |
| No — explanation text only | Score context in prompt only, not response | |

**User's choice:** Yes — return score breakdown in API response

---

## Claude's Discretion

- Exact bell-curve formula (Gaussian vs triangular) — planner picks based on simplicity
- Whether `width` on preferred_popularity_range updates over time or stays fixed
- Bandit cold-start threshold N (recommend 3 per source before bandit overrides statics)

## Deferred Ideas

- Source skipping via bandit (only call top-N sources to save API calls) — decided all 5 sources run; revisit if rate limits hit
- Audio feature weights revival — Spotify endpoint still gone; deferred beyond Phase 4
- Collaborative filtering — explicitly out of scope (PROJECT.md)

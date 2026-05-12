# SongScope — Roadmap

_Created: 2026-05-07_

## Milestone: ML Recommendation Engine v1

**Goal:** Transform SongScope from a rule-based heuristic system into a real content-based ML recommendation engine with a feedback loop, quantifiable success metrics, and interview-ready documentation.

**Success state:** Engine recommends genuinely unknown tracks, like-rate improves over time as feedback accumulates, all ML concepts are implemented and documented.

---

## Phase 1: Fix & Foundation ✓ Complete (2026-05-07)
**Goal:** Eliminate all bugs that corrupt data or produce wrong results. Establish reliable candidate exclusion. Add the missing candidate source. Nothing here is ML yet — just making the pipeline trustworthy.

**Key deliverables:**
- Known-song filter uses persistent DB set (RecommendationLog + DailyGem history) — no more runtime API calls for exclusion
- Top-artist filter logic corrected: filter by track familiarity, not artist familiarity
- `RecommendationLog.liked` written on thumbs up/down so success metrics are non-zero
- `DailyGem.was_liked` synced from feedback
- `Count` import fix + `update_weights` method arity fix
- `artist_related_artists` added as 5th candidate generation strategy
- `RecommendationLog` checked to exclude previously-recommended gems

**Why this first:** Garbage in, garbage out. Scoring and ML improvements mean nothing if the filter is leaking known songs and the feedback signals are never persisted.

**Concepts introduced:** Exclusion sets, candidate generation pipeline, implicit feedback capture

**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md — Test infrastructure (pytest.ini, conftest, fix broken settings path, stub test files)
- [x] 01-02-PLAN.md — personalization_engine fixes (Count import, update_weights arity) + submit_feedback writes RecommendationLog.liked
- [x] 01-03-PLAN.md — hybrid_recommendation_engine: DB exclusion set, remove top-artist filter, add artist_related_artists 5th strategy
- [x] 01-04-PLAN.md — View-level integration tests for DailyGem.was_liked sync (gap closure)

---

## Phase 2: User Taste Vector & Real Scoring ✓ Complete (2026-05-07)
**Goal:** Replace static source weights with a real scoring function. Build a genre-based user taste profile. Score candidates by cosine similarity + novelty factor.

**Key deliverables:**
- Genre frequency vector built from `top_artists` + saved tracks' artists (TF-IDF weighted)
- Popularity preference distribution: model user's typical popularity range (mean ± std of saved tracks)
- Cosine similarity scorer: `genre_sim(candidate_genres, user_taste_vector)`
- Novelty factor: `1 - (popularity / 100)` as explicit score component
- Final score formula: `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`
- Taste vector persisted to `UserProfile.data`
- AI feedback `tempo_weight`, `energy_weight`, `valence_weight` — wire into scoring or remove dead code
- Per-strategy success tracking (replace hardcoded source weights with tracked win rates)

**Why this order:** Taste vector is the foundation. Feedback learning (Phase 3) updates the same vector. Can't do Phase 3 without Phase 2.

**Concepts introduced:** Content-based filtering, cosine similarity, feature engineering, novelty vs relevance trade-off, TF-IDF

---

## Phase 3: Feedback Learning Loop
**Goal:** Make the engine learn. Each like/dislike updates the user's taste vector. Popularity targeting becomes personalized. Multi-armed bandit allocates exploration budget across candidate sources.

**Key deliverables:**
- Online taste vector update on like: `user_vector[genres] += lr * signal`
- Online taste vector update on dislike: `user_vector[genres] -= lr * signal`
- Artist-level feedback multiplier: liked artist → boost, disliked artist → penalize
- Popularity distribution update: liked track → shift target range toward its popularity
- Thompson Sampling bandit over 5 candidate sources (playlist mining, artist network, genre search, related artists, contextual) — each source tracks `(successes, failures)`
- "Why this gem" explanation tied to actual score components (genre match %, novelty score, feedback history)

**Why this order:** Needs Phase 2's scoring function and Phase 1's feedback persistence to be meaningful.

**Concepts introduced:** Implicit feedback learning, online learning, stochastic gradient descent on preference vector, multi-armed bandits, Thompson Sampling, Beta distribution, exploration vs exploitation

---

## Phase 4: Metrics, Evaluation & Documentation
**Goal:** Quantify the system's performance. Visualize taste profile. Produce interview-ready documentation covering every concept in the system.

**Key deliverables:**
- Per-gem metrics persisted: `like_rate`, `novelty_score`, `genre_diversity_score`
- Like-rate trend chart in UI (rolling 7-day window) — the "learning curve" visualization
- Diversity score: pairwise genre distance between recommendations in a session
- "Your taste profile" visualization: genre weight bar chart from taste vector
- Feedback improvement story: before/after like-rate comparison
- `CONCEPTS.md` — comprehensive reference covering:
  - Every ML/DS algorithm used (cosine similarity, Thompson Sampling, online learning, etc.)
  - System architecture: data flow from Spotify → candidates → scoring → feedback
  - Why each design decision was made (API constraints, portfolio rationale)
  - Mathematical formulations for each scoring component
  - Interview talking points for each concept
  - Metrics definitions and what improving them means
- `SYSTEM_DESIGN.md` — architecture diagram + component descriptions

**Why this last:** Metrics need a working feedback loop to be meaningful. Documentation written after implementation is more accurate than before.

**Concepts introduced:** Recommendation evaluation metrics, serendipity, diversity, coverage, precision@k, A/B thinking

**Plans:** 4 plans

Plans:
- [x] 04-01-PLAN.md — Wave 0: install recharts + scaffold backend/tests/test_metrics.py with failing stubs
- [x] 04-02-PLAN.md — Backend metrics endpoints (/api/recommendation-metrics/ + /api/recommendation-trend/) with Jaccard helper
- [ ] 04-03-PLAN.md — Frontend chart components (LikeTrendChart, TasteProfileChart, ImprovementStory, DiversityScore) + wire MetricsStrip into profile/page.tsx
- [ ] 04-04-PLAN.md — Documentation: CONCEPTS.md (ML/DS algorithm reference) + SYSTEM_DESIGN.md (Mermaid architecture diagram)

---

## Phase 5: Security Hardening
**Goal:** Eliminate the three known security issues before any public sharing or deployment: rotate the committed SECRET_KEY, move Spotify credentials server-side only, and re-enable CSRF protection on all feedback endpoints.

**Key deliverables:**
- `SECRET_KEY` moved to environment variable via python-decouple `config()`, old key rotated (new key generated, not committed)
- Spotify `CLIENT_SECRET` removed from `frontend/next.config.mjs` env block; only accessible server-side in Django
- `CsrfExemptSessionAuthentication` removed from `views.py`; `CsrfViewMiddleware` uncommented in `MIDDLEWARE`
- `.env.example` file at repo root (and `backend/.env.example`) documenting all required environment variables
- All existing tests pass after changes

**Why this order:** Security is a prerequisite for sharing the portfolio URL or deploying. Must be done before collaborative filtering (which adds a real user base).

**Concepts introduced:** Secret rotation, CSRF protection, environment variable hygiene, defence in depth

**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Wave 1: Backend security surgery — rotate SECRET_KEY via decouple + uncomment CsrfViewMiddleware + delete CsrfExemptSessionAuthentication dead code
- [x] 05-02-PLAN.md — Wave 1: Frontend credential exposure removal — strip env block + dotenv import from next.config.mjs
- [x] 05-03-PLAN.md — Wave 2: Create .env.example (root + backend/) + run full regression test suite + record manual smoke-test checklist

---

## Dependency Order

```
Phase 1 (bugs + foundation)
    → Phase 2 (taste vector + scoring)
        → Phase 3 (feedback learning)
            → Phase 4 (metrics + docs)
                → Phase 5 (security hardening)
```

All sequential — each phase depends on the previous.

---

## Security (Deferred)

Security hardening (SECRET_KEY rotation, CSRF re-enable, client secret removal from browser bundle) is intentionally deferred. This is a portfolio project. Security will be addressed after the ML engine is complete.

Tracked in PROJECT.md Active requirements for future milestone.

---

_Last updated: 2026-05-12_

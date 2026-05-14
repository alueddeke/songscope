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

---

## Milestone: v1.1 — Explainability + Feedback Loop Closure

**Goal:** Surface why each daily gem was chosen (score breakdown + explanation text) and close the feedback loop with a measurable compound success metric (hit = liked OR saved).

**Success state:** Every gem card shows what drove the pick, explanation text is tied to the actual score formula, and the metrics strip reports a compound hit rate backed by real outcome data.

---

## Phases

- [ ] **Phase 6: Schema Migration** — Add all new DailyGem fields in a single migration (score_breakdown, score_total, was_saved, taste_vector_snapshot)
- [ ] **Phase 7: Backend Wiring** — Write score fields at recommendation time, fix all three cached-branch return sites, wire was_saved, expose compound hit rate
- [ ] **Phase 8: Frontend Score Breakdown** — Render the three score bars and compound hit rate in the UI
- [ ] **Phase 9: Documentation Sync** — Update CONCEPTS.md and SYSTEM_DESIGN.md to reflect all v1.1 changes

---

## Phase Details

### Phase 6: Schema Migration
**Goal**: The database has all fields required for score persistence, compound success tracking, and taste snapshot logging
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: SCHEMA-01, METRIC-01
**Success Criteria** (what must be TRUE):
  1. `DailyGem` table contains `score_breakdown` (JSONField), `score_total` (FloatField nullable), `was_saved` (BooleanField nullable), and `taste_vector_snapshot` (JSONField nullable) columns after running `migrate`
  2. All existing `DailyGem` rows survive migration with no data loss — new columns default to `{}` / `null` as designed
  3. Django ORM can write and read each new field in the shell without error
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md — Add 4 fields to DailyGem model + auto-generate migration 0008 (score_breakdown, score_total, was_saved, taste_vector_snapshot)
- [ ] 06-02-PLAN.md — TestDailyGemNewFields ORM round-trip tests + full backend regression suite

### Phase 7: Backend Wiring
**Goal**: The API returns populated score breakdowns and explanation text for every gem request, was_saved is recorded on library saves, and compound hit rate is available in the metrics endpoint
**Depends on**: Phase 6
**Requirements**: SCHEMA-02, SCHEMA-03, SCHEMA-04, EXPLAIN-01, EXPLAIN-02, METRIC-02
**Success Criteria** (what must be TRUE):
  1. Calling `GET /api/daily-gem/` on a fresh day returns a non-empty `score_breakdown` dict and a human-readable `explanation` string derived from the dominant score component — no OpenAI call involved
  2. Calling `GET /api/daily-gem/` a second time the same day (cached branch) returns the same non-empty `score_breakdown` and `explanation` read from the DB — not hardcoded `{}`
  3. Clicking the heart/save button triggers `DailyGem.was_saved = True` in the DB; a failure to write is non-fatal and does not 500 the save action
  4. `GET /api/recommendation-metrics/` returns a `compound_hit_rate` key computed as `(was_liked OR was_saved) / total_gems`
**Plans**: TBD

### Phase 8: Frontend Score Breakdown
**Goal**: Users can see what drove their daily gem pick directly on the gem card, and the metrics strip shows compound hit rate
**Depends on**: Phase 7
**Requirements**: EXPLAIN-03, METRIC-03
**Success Criteria** (what must be TRUE):
  1. The gem card displays three labeled score bars (Genre Match, Novelty, Feedback Influence) with percentage values rounded to the nearest 5%, rendered from `score_breakdown` API data
  2. Gems with no score data (pre-migration rows) display a graceful empty state — no crash, no blank bars
  3. The MetricsStrip shows a "Hit Rate" tile sourced from `compound_hit_rate` alongside the existing gem acceptance rate
**Plans**: TBD
**UI hint**: yes

### Phase 9: Documentation Sync
**Goal**: CONCEPTS.md and SYSTEM_DESIGN.md accurately reflect every v1.1 change so the codebase remains interview-ready
**Depends on**: Phase 7
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. CONCEPTS.md contains: compound hit rate definition with OR-semantics rationale, `taste_vector_snapshot` purpose (offline evaluation), score breakdown persistence rationale, and why the explanation is deterministic (not OpenAI)
  2. SYSTEM_DESIGN.md contains: updated `DailyGem` field table with all v1.1 columns, `_build_gem_explanation` data flow description, `add_track_to_liked` side-effect note for `was_saved`, and Score Breakdown API contract
**Plans**: TBD

---

## Progress Table (v1.1)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Schema Migration | 0/2 | Not started | - |
| 7. Backend Wiring | 0/? | Not started | - |
| 8. Frontend Score Breakdown | 0/? | Not started | - |
| 9. Documentation Sync | 0/? | Not started | - |

---

## Dependency Order (v1.1)

```
Phase 6 (schema migration)
    → Phase 7 (backend wiring)
        → Phase 8 (frontend score breakdown)
        → Phase 9 (documentation sync)
```

Phase 9 can begin after Phase 7 completes; it does not block Phase 8.

---

_Last updated: 2026-05-13_

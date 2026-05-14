# SongScope

## Current Milestone: v1.1 Explainability + Feedback Loop Closure

**Goal:** Surface why each recommendation was chosen and close the feedback loop with a real compound success metric.

**Target features:**
- "Why this gem" score breakdown in UI (genre match %, novelty score, feedback multiplier contribution)
- Compound success metric: binary hit = played + saved/liked
- Per-recommendation outcome logging (was it played? saved? skipped?)
- Explanation text tied to actual score components, not canned copy

---

## What This Is

SongScope is a daily music discovery app that connects to a user's Spotify account and surfaces one "hidden gem" per day — a song the user hasn't heard before but is likely to love, based on their listening patterns, taste, and real-time feedback. It is primarily a portfolio project demonstrating full-stack development, ML-backed recommendation systems, and data science skills — designed to generate substantive interview talking points.

## Core Value

Recommend one song per day that the user genuinely discovers — not a song they already know — using a machine learning model that measurably improves from their feedback.

## Requirements

### Validated

- ✓ Spotify OAuth login and token refresh — existing
- ✓ User profile page with top artists display — existing
- ✓ Daily Gem generation (one recommendation per day) — existing
- ✓ Playlist mining strategy (find overlooked songs from user playlists) — existing
- ✓ Artist deep track discovery (unlistened songs from liked artists) — existing
- ✓ Time-of-day listening pattern signal — existing
- ✓ Thumbs up / thumbs down feedback UI — existing
- ✓ Natural language feedback → OpenAI structured interpretation — existing
- ✓ Rate limiting on API calls — existing
- ✓ Recommendation metrics display strip — existing

### Validated in Phase 1 (Fix & Foundation — 2026-05-07)

- ✓ Filter already-known songs: DB-backed exclusion set using RecommendationLog + DailyGem history
- ✓ Fix broken test suite: pytest.ini, conftest, settings path fixed; 31 tests collected, all pass
- ✓ `Count` import fixed in personalization_engine; `update_weights` arity crash fixed
- ✓ `RecommendationLog.liked` written on LIKE/DISLIKE/unlike — feedback signals non-zero
- ✓ `DailyGem.was_liked` synced from submit_feedback view
- ✓ Top-artist name filter corrected to track-level exclusion
- ✓ `artist_related_artists` added as 5th candidate generation strategy

### Validated in Phase 2 (User Taste Vector & Real Scoring — 2026-05-07)

- ✓ Genre taste vector built from `top_artists` data and persisted to `UserProfile.data['taste_vector']`
- ✓ Cosine similarity scorer implemented: `genre_sim(candidate_genres, user_taste_vector)`
- ✓ Final score formula wired: `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`
- ✓ Dead AI audio-weight code (`_update_weights_from_ai_feedback`) removed — deprecated Spotify endpoint
- ✓ `RecommendationLog.source` CharField added + migration 0006 applied — per-strategy tracking ready
- ✓ 21 Phase 2 tests pass (taste vector, cosine scoring, source field DB persistence)

### Validated in Phases 3–5 (Feedback Learning + Security — 2026-05-12)

- ✓ Online taste vector update on like/dislike (Phase 3)
- ✓ Thompson Sampling bandit over 5 candidate sources (Phase 3)
- ✓ SECRET_KEY rotated to env var via python-decouple (Phase 5)
- ✓ Spotify CLIENT_SECRET removed from frontend bundle (Phase 5)
- ✓ CsrfViewMiddleware re-enabled (Phase 5)
- ✓ OAUTHLIB_INSECURE_TRANSPORT production guard added (Phase 5 review)
- ✓ Raw str(e) exception leaks plugged across all 14 handlers (Phase 5 review)

### Validated in Phase 6 (Schema Migration — 2026-05-14)

- ✓ `DailyGem.score_breakdown` (JSONField, default=dict) added — score persistence foundation (SCHEMA-01)
- ✓ `DailyGem.score_total` (FloatField, null/blank) added — denormalized score for metrics queries (SCHEMA-01)
- ✓ `DailyGem.was_saved` (BooleanField, null/blank) added — compound success metric signal (METRIC-01)
- ✓ `DailyGem.taste_vector_snapshot` (JSONField, null/blank) added — recommendation model state capture (SCHEMA-01)
- ✓ Migration 0008 auto-generated and applied; `makemigrations --check` clean; 113 tests pass, zero regressions
- ✓ ORM round-trip tests (10 methods in `TestDailyGemNewFields`) validate all 4 new columns

### Active (v1.1 target)

- [ ] "Why this gem" score breakdown in UI — genre match %, novelty score, feedback multiplier contribution
- [ ] Compound success metric: binary hit = played + saved/liked
- [ ] Per-recommendation outcome logging (was it played? saved? skipped?)
- [ ] Explanation text tied to actual score components (not canned copy)

### Active (future milestones)

- [ ] Evaluation dashboard — learning curve, per-source win rates, A/B framework
- [ ] Audio feature proxy — replace deprecated Spotify audio_features with AcousticBrainz/Last.fm
- [ ] Re-wire hit-prediction dataset as cold-start priors
- [ ] Collaborative filtering (item-item CF + hybrid blend)
- [ ] Production deployment (Vercel + Railway/Render + Postgres)

### Out of Scope

- Collaborative filtering across users — no user base yet; design for it later
- Native mobile app — web-first, Spotify already has mobile
- Social features (sharing gems, following users) — portfolio focus, not a social product
- Spotify Premium features — don't require or gate on Premium
- Song playback controls beyond 30s preview — Spotify handles full playback
- Playlist creation/editing — recommendation output only, not playlist management

## Context

**Origin:** Built out of a bootcamp hackathon win → Data Science course → ML hit-prediction project → full-stack app. The hit-prediction model used audio features (energy, danceability, acousticness, instrumentalness) to predict chart success with >90% accuracy using supervised learning with SMOTE-style balancing.

**Spotify API deprecations:** `sp.audio_features` and `sp.recommendations` endpoints are gone. The entire recommendation strategy had to pivot from audio-feature-similarity to playlist mining + artist discovery + time-of-day signals. This means the original dataset's features (BPM, energy, etc.) cannot be fetched for new songs via Spotify — but the dataset itself and trained weights may still be useful if another data source provides those features.

**Current engine state (post Phase 2):** `HybridRecommendationEngine` has a working exclusion pipeline, 5 candidate strategies, and a real cosine-similarity scoring function backed by a genre taste vector. Feedback persistence is wired. Source tracking is wired. Test suite has 47 passing tests. Remaining work:
1. ~~Recommendations include songs the user already knows~~ — Fixed (Phase 1)
2. ~~Static source weights — no ML scoring~~ — Fixed (Phase 2): cosine similarity + novelty formula
3. ~~`RecommendationLog.liked` is never updated~~ — Fixed (Phase 1)
4. ~~Personalization engine crash on use~~ — Fixed (Phase 1)
5. Taste vector does not update from feedback — next phase (Phase 3)

**ML approach:** Content-based filtering is the right starting point for single-user. Build a user preference vector from their listening data, score candidate tracks against it, rank by score × novelty. Scikit-learn level — implementable, explainable in interviews, extensible to collaborative filtering later.

**Success signal:** Compound metric — track was played AND user saved/liked it. Treat it as a binary classification problem: each recommendation is either a hit (listened + liked) or a miss.

**Dataset:** Original hit-prediction dataset is available. Audio features were the training features. If a supplementary dataset (e.g., Million Song Dataset, Last.fm) provides audio features for modern tracks, these base weights may remain relevant as cold-start priors.

## Constraints

- **Tech stack**: Django REST + Next.js + SQLite — already established, no migrations to new stack
- **Spotify API**: Only endpoints available as of 2026 — no audio_features, no recommendations; must work with liked songs, playlists, recently played, top artists, top tracks, artist albums
- **OpenAI**: Rate limited to ~$1/day budget; feedback interpretation and gem explanations only
- **Single user**: No user base for collaborative signals yet — content-based only for now
- **Portfolio**: Code must be readable and explainable; no black-box solutions without understanding
- **Interview-ready**: ML components must be documentable with math, rationale, and talking points

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Content-based filtering as ML approach | No multi-user base; cosine similarity on user preference vector is explainable and implementable | Implemented (Phase 2) |
| Drop TF-IDF weighting for taste vector | Simple frequency count is sufficient for portfolio scope; TF-IDF adds complexity without meaningful gain at this scale | Validated (Phase 2) |
| Remove audio-weight dead code | `_update_weights_from_ai_feedback` adjusted deprecated Spotify audio features — permanently inapplicable | Validated (Phase 2) |
| Compound metric (listened + liked) | Click-through alone is a weak signal; save/like confirms genuine discovery | Target: v1.1 Phase 6 |
| Keep original dataset for cold-start priors | If audio features available from alt source, base weights give a head start on taste modeling | — Deferred |
| Filter known songs before scoring | Core UX failure; must happen before any ML improvement matters | Validated (Phase 1) |
| SQLite for now | Portfolio scale; easy to demo; migrate to Postgres when/if multi-user | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-13 — Milestone v1.0 complete; v1.1 started*

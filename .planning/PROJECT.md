# SongScope

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

### Active

- [ ] ML-backed recommendation scoring — replace rule-based heuristics with a trained model
- [ ] Wire AI feedback weights into actual recommendation ranking (currently stored but ignored)
- [ ] Compound success metric tracking: user listened AND liked/saved recommended track
- [ ] Per-recommendation outcome logging (was it played? saved? skipped?)
- [ ] Security hardening (rotate SECRET_KEY, move credentials to env vars, re-enable CSRF)
- [ ] Explore viability of original hit-prediction dataset as base weights for ML model
- [ ] Research and document current available Spotify endpoints and their data shape

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

**Current engine state (post Phase 1):** `HybridRecommendationEngine` has a working exclusion pipeline and 5 candidate strategies. Known-song filtering is DB-backed. Feedback persistence is wired. Test suite is clean. Remaining work:
1. ~~Recommendations include songs the user already knows~~ — Fixed (Phase 1)
2. AI feedback weights are stored but never applied to scoring
3. ~~`RecommendationLog.liked` is never updated~~ — Fixed (Phase 1)
4. ~~Personalization engine crash on use~~ — Fixed (Phase 1)

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
| Content-based filtering as ML approach | No multi-user base; cosine similarity on user preference vector is explainable and implementable | — Pending |
| Compound metric (listened + liked) | Click-through alone is a weak signal; save/like confirms genuine discovery | — Pending |
| Keep original dataset for cold-start priors | If audio features available from alt source, base weights give a head start on taste modeling | — Pending |
| Filter known songs before scoring | Core UX failure; must happen before any ML improvement matters | — Pending |
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
*Last updated: 2026-05-07 — Phase 1 complete*

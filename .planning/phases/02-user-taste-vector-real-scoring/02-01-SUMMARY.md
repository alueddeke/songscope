---
phase: "02"
plan: "02-01"
subsystem: recommendations
tags: [ml-scoring, taste-vector, cosine-similarity, content-based-filtering]
dependency_graph:
  requires: [01-04]
  provides: [taste-vector-in-profile, locked-scoring-formula, clean-dead-code]
  affects: [hybrid_recommendation_engine]
tech_stack:
  added: []
  patterns: [cosine-similarity-genre-vectors, locked-score-formula]
key_files:
  created: []
  modified:
    - backend/apps/recommendations/hybrid_recommendation_engine.py
decisions:
  - "Genre taste vector built from top_artists (flat count per genre occurrence) — stored as raw counts in UserProfile.data['taste_vector']; cosine similarity normalizes at score time"
  - "Locked formula 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier — weights match ROADMAP exactly and must not be adjusted"
  - "Artist genre lookup at score time uses already-fetched top_artists data — zero extra Spotify API calls introduced"
  - "Dead _update_weights_from_ai_feedback() removed — audio_features endpoint gone from Spotify API so all three weight keys (tempo_weight, energy_weight, valence_weight) were permanently unapplied"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-07T23:21:41Z"
  tasks_completed: 3
  files_modified: 1
---

# Phase 02 Plan 01: Genre Taste Vector and Cosine Similarity Scoring Summary

Genre frequency vector built from top_artists and wired into profile refresh; scoring replaced with cosine similarity formula (0.4 genre_sim + 0.3 novelty + 0.3 feedback_multiplier); dead AI audio-weight code deleted.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| T1 | Add _build_taste_vector() and wire into _update_profile_data() | 50f93b0b |
| T2 | Replace _score_recommendations() with cosine similarity formula + _cosine_similarity() helper | 50f93b0b |
| T3 | Delete _update_weights_from_ai_feedback() dead code | 50f93b0b |

## What Was Built

### _build_taste_vector()
Iterates over `UserProfile.data['base_data']['top_artists']`, counts genre occurrences across all top artists, and stores the result as `UserProfile.data['taste_vector'] = {"indie rock": 7, "folk": 4, ...}`. Vector is raw counts (not normalized) — cosine similarity normalizes at score time, keeping the stored vector human-readable for Phase 4 visualization.

Wired into `_update_profile_data()` immediately before `self.profile.save()`, so it refreshes alongside the top_artists fetch at every profile update cadence.

### _cosine_similarity()
Epsilon-free implementation using `np.linalg.norm` with explicit zero-norm guard: returns 0.0 if either input dict is empty or either vector has zero norm. Operates on the union of keys from both dicts to handle the sparse vector case correctly.

### _score_recommendations() — new body
Locked formula:
```
score = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier
```
- `genre_sim`: cosine similarity between `{genre: 1.0 for genre in artist_genres}` and `taste_vector`
- `novelty`: `1.0 - (popularity / 100.0)` using popularity already on recommendation dicts
- `feedback_multiplier`: 1.5 for liked artist, 0.5 for disliked artist, 1.0 for neutral
- Artist genre lookup reads from already-fetched `top_artists` in profile data — zero extra API calls
- All profile data access uses `.get()` chains — safe on empty/new profiles

### Dead code removal
`_update_weights_from_ai_feedback()` (37 lines) deleted. Its three weight keys (`tempo_weight`, `energy_weight`, `valence_weight`) are permanently unapplicable because Spotify's `audio_features` endpoint was deprecated. The call to this method inside `add_ai_feedback()` was also removed; `add_ai_feedback()` otherwise unchanged — it still stores AI feedback history in the profile.

## Truths Verified

- `UserProfile.data['taste_vector']` is populated after every profile refresh
- `_score_recommendations()` computes score with exactly `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`
- `_cosine_similarity()` returns 0.0 when either input dict is empty
- `genre_sim` is 0.0 when candidate artist is not in user's top_artists
- `feedback_multiplier` = 1.5 / 0.5 / 1.0 for liked / disliked / neutral artists
- `novelty` = `1.0 - (popularity / 100.0)`
- `_update_weights_from_ai_feedback()` no longer exists in the file
- `add_ai_feedback()` no longer calls `_update_weights_from_ai_feedback()` but otherwise unchanged
- No extra Spotify API calls introduced
- All profile data access uses `.get()` chains

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all scoring components are fully wired. `taste_vector` is populated from real top_artists data on profile refresh. `novelty` reads the `popularity` field already present on recommendation dicts. `feedback_multiplier` reads from the `liked_artists`/`disliked_artists` lists already populated by `add_feedback()`.

## Threat Flags

No new threat surface introduced. The threat model mitigations were applied:
- T-02-01: Zero-norm guard in `_cosine_similarity()` via explicit `norm_a == 0.0 or norm_b == 0.0` check + early return 0.0 on empty inputs
- T-02-02: All profile data access uses `.get()` chains with empty-dict/list defaults
- T-02-04: Artist lookup is read-only against profile data; no SQL or shell execution

## Self-Check: PASSED

- [x] `backend/apps/recommendations/hybrid_recommendation_engine.py` modified and committed (50f93b0b)
- [x] `grep -c "_build_taste_vector"` returns 2
- [x] `grep -c "_cosine_similarity"` returns 2
- [x] Formula line present exactly once
- [x] `_update_weights_from_ai_feedback` count = 0
- [x] `python -c "import ast; ast.parse(...)"` returns OK
- [x] `python manage.py check` returns 0 issues

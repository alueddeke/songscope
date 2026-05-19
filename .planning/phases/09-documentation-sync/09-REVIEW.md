---
phase: 09-documentation-sync
reviewed: 2026-05-19T12:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - CONCEPTS.md
  - SYSTEM_DESIGN.md
findings:
  critical: 2
  warning: 3
  info: 0
  total: 5
status: issues_found
---

# Phase 09: Code Review Report — Documentation Sync

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Both documentation files were reviewed against live source code in `backend/apps/recommendations/hybrid_recommendation_engine.py`, `backend/apps/recommendations/personalization_engine.py`, and `backend/apps/core/views.py`.

The documents are substantially accurate and well-structured. Most algorithmic descriptions — cosine similarity, Thompson Sampling (formula, normalization, code snippet), novelty bell-curve, Jaccard distance, compound scoring formula, and gem explanation templates — match the implementation exactly. The previous review cycle (existing REVIEW.md) identified issues that have been correctly addressed in the current files.

Two factual errors remain. The more serious is a wrong description of how `hidden_gem_rate` is computed: CONCEPTS.md says it counts tracks with popularity < 40 **that were liked**, but the code counts all recommended tracks with popularity < 40 regardless of like status — a different metric. The second is that the `apply_feedback_learning` code snippet shown in CONCEPTS.md is a truncated, outdated version that omits the `TASTE_VECTOR_MAX` cap and the entire bandit `source_stats` update block, even though the paragraph immediately after the snippet says "the same function also updates `source_stats`."

Three warnings cover: the undocumented 50-track cap on diversity computation (which also makes the O(N²) complexity claim in SYSTEM_DESIGN.md misleading), and the claim that five distinct candidate sources are active when `genre_search` is never called in `get_recommendations()`.

---

## Critical Issues

### CR-01: `hidden_gem_rate` described as requiring `was_liked=True` — code does not filter by like status

**File:** `CONCEPTS.md:302`

**Issue:** CONCEPTS.md describes the serendipity proxy as:
> "In the metrics endpoint this is approximated as `hidden_gem_rate` (tracks with popularity < 40 **that were liked**)"

The formula block at line 312 reinforces this: `serendipity ≈ hidden_gem_rate (approx: popular < 40 and was_liked)`.

The actual implementation in `backend/apps/core/views.py:432-434` is:
```python
hidden_gem_rate = round(
    gems.filter(track_popularity__lt=40).count() / gem_total, 4
)
```
There is no `was_liked` filter. `hidden_gem_rate` is the fraction of *all recommended gems* (liked or not, including those with `was_liked=None`) that had popularity below 40. It is a measure of how often the engine recommends underground tracks, not how often the user liked underground tracks. This is a meaningfully different metric: a high `hidden_gem_rate` with a low `gem_acceptance_rate` would indicate the engine recommends obscure tracks the user does not enjoy — the opposite of serendipity as documented.

**Fix:** Correct both the inline description (line 302) and the formula comment (line 312):
```
hidden_gem_rate = fraction of all recommended gems where track_popularity < 40
                  (regardless of was_liked status — measures how often the engine
                  recommends underground tracks, not user satisfaction with them)
serendipity ≈ hidden_gem_rate * gem_acceptance_rate  (more accurate proxy)
```

---

### CR-02: `apply_feedback_learning` code snippet in CONCEPTS.md is truncated and omits the TASTE_VECTOR_MAX cap and the entire bandit update block

**File:** `CONCEPTS.md:206-239`

**Issue:** The code snippet shown ends at `profile.save(update_fields=['data'])` after line 238. The actual function in `personalization_engine.py` has two significant differences that are invisible in the snippet:

**1. Missing TASTE_VECTOR_MAX cap on LIKE updates (line 287-290):**
The snippet shows:
```python
taste_vector[genre] = taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR
```
The real code is:
```python
TASTE_VECTOR_MAX = 5.0  # cap prevents unbounded growth from like/unlike cycles
taste_vector[genre] = min(taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR, TASTE_VECTOR_MAX)
```
The formula section at line 194 also omits this cap, showing the LIKE update as unbounded.

**2. Missing bandit source_stats update block (lines 304-316):**
The paragraph after the snippet (line 241) states "The same function also updates `source_stats` for the Thompson bandit — a like increments `s` for the source that produced the track, a dislike increments `f`." But the snippet itself does not show this code at all. A reader who copies the snippet would build a function that silently omits the bandit update and thereby breaks Thompson Sampling's feedback loop. The snippet contradicts the immediately following prose.

**Fix:** Update the code snippet to include both the `TASTE_VECTOR_MAX` cap and the `source_stats` block. Update the Formula section to add:
```
LIKE update is also capped above:
    taste_vector[g] = min(taste_vector[g] + lr, TASTE_VECTOR_MAX)
    where TASTE_VECTOR_MAX = 5.0
```

---

## Warnings

### WR-01: Both documents list `genre_search` as an active candidate source — it is defined in SOURCE_DEFAULTS but never called

**File:** `CONCEPTS.md:108`, `SYSTEM_DESIGN.md:148-153`

**Issue:** CONCEPTS.md introduces Thompson Sampling with: "SongScope generates candidates from five distinct sources (playlist mining, artist network, **genre search**, related artists, contextual)." SYSTEM_DESIGN.md's Recommendation Engine component lists the same five verified strategy names.

`get_recommendations()` in `hybrid_recommendation_engine.py` calls only four strategies:
- Strategy 1: `_get_playlist_recommendations` → `playlist_mining`
- Strategy 2: `_get_artist_network_recommendations` → `artist_network`
- Strategy 3: `_get_contextual_recommendations` → `contextual`
- Strategy 5 (comment says 5, no Strategy 4): `_get_related_artist_recommendations` → `related_artists`

There is no call to any `genre_search` method. `genre_search` appears in `SOURCE_DEFAULTS` at line 38 but no candidate is ever tagged with `source='genre_search'` during normal operation. As a result, the Thompson bandit never accumulates `source_stats` for `genre_search`, and the claim of five active sources is factually incorrect — the system uses four.

**Fix:** In both documents, change "five distinct sources" to "four active sources" and update the source lists. Add a note that `genre_search` is reserved in `SOURCE_DEFAULTS` for a planned future strategy.

---

### WR-02: Jaccard diversity formula says "all N*(N-1)/2 pairs" — implementation caps at 50 most recent tracks

**File:** `CONCEPTS.md:255`, `CONCEPTS.md:264`

**Issue:** CONCEPTS.md states: "The overall diversity score is the mean pairwise Jaccard distance across **all N*(N-1)/2 pairs** in the recommendation history."

The actual code in `views.py:479`:
```python
sample = nonempty[-50:]  # cap at 50 most recent to avoid O(n²) blowup
pairs = list(combinations(sample, 2))
```
Only the 50 most recent non-empty genre lists are used. For a user with more than 50 liked/disliked tracks, older tracks are silently excluded from the diversity calculation. The documented formula and the implementation compute different things once the user has more than 50 feedback events.

**Fix:** Update the formula description and the Known Limitation block to reflect the cap:
```
diversity_score = mean( J(A_i, A_j) )  for all pairs in the 50 most recent
                  non-empty genre lists  (capped to avoid O(n²) growth)
```

---

### WR-03: SYSTEM_DESIGN.md Operational Constraints cites O(N²) with 66,000 pairs at 365 gems — the 50-track cap makes the actual worst case 1,225 pairs

**File:** `SYSTEM_DESIGN.md:257`

**Issue:** The Operational Constraints section states:
> "Jaccard diversity is O(N^2) in the number of gems. At 365 gems/year the full pairwise computation is ~66,000 pairs — acceptable, but worth caching at higher volumes."

Because the implementation caps at 50 tracks (`sample = nonempty[-50:]`), the actual maximum number of pairs is `50*49/2 = 1,225` — independent of how many total gems the user has. The 66,000-pair figure and the "at higher volumes" concern are both incorrect for the current implementation. An interviewer reading this after seeing the code would notice the discrepancy.

**Fix:** Update to reflect the bounded computation:
> "Jaccard diversity iterates over the 50 most recently rated tracks (capped). Worst case is 50×49/2 = 1,225 pairs — negligible. If the cap were removed, it would be O(N²) in the number of tracks with genre data."

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

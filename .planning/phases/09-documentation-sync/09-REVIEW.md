---
phase: 09-documentation-sync
reviewed: 2026-05-19T14:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - CONCEPTS.md
  - SYSTEM_DESIGN.md
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 09: Code Review Report — Documentation Sync

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Both documentation files were reviewed against live source code in `backend/apps/recommendations/hybrid_recommendation_engine.py`, `backend/apps/recommendations/personalization_engine.py`, and `backend/apps/core/views.py`.

The documents are largely well-structured and accurate on the mathematical descriptions — cosine similarity, novelty bell-curve formula, Thompson Sampling, Jaccard distance, compound scoring formula, and gem explanation templates all match the implementation. However, two factual errors in CONCEPTS.md would actively mislead an interviewer or developer who cross-checks against the codebase.

The more serious is that `hidden_gem_rate` is described as counting tracks that were liked AND had low popularity; the code has no `was_liked` filter and counts all low-popularity gems regardless of feedback. The second is that the `apply_feedback_learning` code snippet is materially truncated: it omits the `TASTE_VECTOR_MAX = 5.0` cap on LIKE updates and the entire bandit `source_stats` update block, while the prose after the snippet explicitly claims that block exists. Both are contradictions provable by diffing the snippet against the actual file.

Four warnings cover: the false claim of five active candidate sources (only four are called; `genre_search` is never invoked), the undocumented 50-track cap on diversity computation that makes the "all N*(N-1)/2 pairs" formula description wrong, the resulting incorrect 66,000-pair complexity figure in SYSTEM_DESIGN.md, and stale line number citations in every CONCEPTS.md code snippet header.

---

## Critical Issues

### CR-01: `hidden_gem_rate` described as requiring `was_liked=True` — code applies no such filter

**File:** `CONCEPTS.md:302,312`

**Issue:** CONCEPTS.md line 302 states:
> "In the metrics endpoint this is approximated as `hidden_gem_rate` (tracks with popularity < 40 **that were liked**)"

The formula block at line 312 reinforces this: `serendipity ≈ hidden_gem_rate (approx: popular < 40 and was_liked)`.

The actual implementation in `backend/apps/core/views.py:432-434`:
```python
hidden_gem_rate = round(
    gems.filter(track_popularity__lt=40).count() / gem_total, 4
)
```
There is no `was_liked` filter. `hidden_gem_rate` is the fraction of *all recommended gems* (liked, disliked, or unrated) with popularity below 40. It measures how often the engine recommends underground tracks, not how often the user liked them.

This is a meaningfully different metric: a high `hidden_gem_rate` combined with a low `gem_acceptance_rate` indicates the engine is pushing obscure tracks the user rejects — the opposite of what the documentation implies. An interviewer who tests this interpretation against the code will find the discrepancy immediately.

**Fix:** Correct both line 302 and line 312:
```
hidden_gem_rate = fraction of all recommended gems where track_popularity < 40
                  (no was_liked filter — measures how often underground tracks are
                  recommended, not whether the user enjoyed them)
serendipity      ≈ hidden_gem_rate * gem_acceptance_rate  (more accurate proxy)
```
Also update line 323's inline note: change `(popularity < 40)` to `(popularity < 40, regardless of was_liked)`.

---

### CR-02: `apply_feedback_learning` code snippet omits `TASTE_VECTOR_MAX` cap and the entire bandit update block

**File:** `CONCEPTS.md:206-239`

**Issue:** The code snippet shown for `apply_feedback_learning` ends at `profile.save(update_fields=['data'])` at line 238. The actual function in `personalization_engine.py` (lines 254-324) has two significant additions invisible in the snippet:

**1. Missing `TASTE_VECTOR_MAX` cap on LIKE updates (actual code lines 287-290):**

The snippet shows the LIKE branch as:
```python
taste_vector[genre] = taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR
```
The real code is:
```python
TASTE_VECTOR_MAX = 5.0  # cap prevents unbounded growth from like/unlike cycles
taste_vector[genre] = min(taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR, TASTE_VECTOR_MAX)
```
The Formula section at line 194 also omits this cap, showing the LIKE update as unbounded — a direct contradiction with the actual behaviour.

**2. Missing `source_stats` bandit update block (actual code lines 303-316):**

The paragraph immediately following the snippet (line 241) explicitly states:
> "The same function also updates `source_stats` for the Thompson bandit — a like increments `s` for the source that produced the track, a dislike increments `f`."

The snippet does not contain this logic at all. A developer who copies the snippet to understand or reimplement the function would produce code that silently omits the bandit update and breaks Thompson Sampling's feedback loop. The snippet directly contradicts the prose that describes it.

**Fix:** Update the code snippet to include both the `TASTE_VECTOR_MAX` cap and the `source_stats` block. Update the Formula section to add:
```
LIKE update is capped above:
    taste_vector[g] = min(taste_vector[g] + lr, TASTE_VECTOR_MAX)
    where TASTE_VECTOR_MAX = 5.0
```

---

## Warnings

### WR-01: Both documents claim five active candidate sources — `genre_search` is never called in `get_recommendations()`

**File:** `CONCEPTS.md:108`, `SYSTEM_DESIGN.md:148-153`

**Issue:** CONCEPTS.md line 108 states: "SongScope generates candidates from **five distinct sources** (playlist mining, artist network, genre search, related artists, contextual)." SYSTEM_DESIGN.md lists the same five as "verified strategy names."

`get_recommendations()` in `hybrid_recommendation_engine.py` calls only four strategies:
- Strategy 1: `_get_playlist_recommendations` → `playlist_mining`
- Strategy 2: `_get_artist_network_recommendations` → `artist_network`
- Strategy 3: `_get_contextual_recommendations` → `contextual`
- Strategy 5 (comment skips 4): `_get_related_artist_recommendations` → `related_artists`

No method with `genre_search` in its name exists or is called. `genre_search` appears in `SOURCE_DEFAULTS` at line 38 with a default weight of 0.2, but no candidate is ever tagged `source='genre_search'` during normal operation. The Thompson bandit never accumulates `source_stats` for `genre_search` and it never influences recommendations. The claim of five active sources is factually incorrect.

**Fix:** In both documents, change "five distinct sources" to "four active sources" and remove `genre_search` from the active source lists. Add a note that `genre_search` is defined in `SOURCE_DEFAULTS` as a reserved slot for a planned future strategy.

---

### WR-02: Jaccard diversity formula describes "all N*(N-1)/2 pairs" — implementation caps at 50 most recent tracks

**File:** `CONCEPTS.md:255,264`

**Issue:** CONCEPTS.md line 255 states: "The overall diversity score is the mean pairwise Jaccard distance across **all N*(N-1)/2 pairs** in the recommendation history."

The actual code at `views.py:479`:
```python
sample = nonempty[-50:]  # cap at 50 most recent to avoid O(n²) blowup
pairs = list(combinations(sample, 2))
```
Only the 50 most recent non-empty genre lists are used. For users with more than 50 feedback events, older tracks are silently excluded. The documented formula and the implementation compute different quantities once the user accumulates more than 50 genre-populated gems.

**Fix:** Update the formula description at line 255 and the Known Limitation block:
```
diversity_score = mean( J(A_i, A_j) ) for all pairs in the 50 most recent
                  non-empty genre lists (capped at 50 to bound computation)
```

---

### WR-03: SYSTEM_DESIGN.md Operational Constraints cites 66,000 pairs at 365 gems — 50-track cap makes actual worst case 1,225 pairs

**File:** `SYSTEM_DESIGN.md:257`

**Issue:** The Operational Constraints section states:
> "Jaccard diversity is O(N^2) in the number of gems. At 365 gems/year the full pairwise computation is ~66,000 pairs — acceptable, but worth caching at higher volumes."

Because the implementation caps at 50 tracks (`sample = nonempty[-50:]`), the actual maximum number of pairs is `50*49/2 = 1,225`, independent of how many total gems the user has. The 66,000-pair figure, the "at higher volumes" concern, and the O(N²) complexity characterization are all incorrect for the current implementation. An interviewer reading SYSTEM_DESIGN.md and then checking the code would flag this discrepancy.

**Fix:**
> "Jaccard diversity iterates over the 50 most recently rated tracks (capped in code). Worst case is 50×49/2 = 1,225 pairs — negligible. If the cap were removed, complexity would be O(N²) in the number of tracks with non-empty genre data."

---

### WR-04: All code snippet line-number citations in CONCEPTS.md are stale (off by 5 lines)

**File:** `CONCEPTS.md:39,81,127,376,431`

**Issue:** Every source comment in CONCEPTS.md code snippets cites line numbers that are approximately 5 lines lower than the actual current locations in the source files:

| CONCEPTS.md claims | Actual location |
|---|---|
| `_cosine_similarity` at lines 813-824 | Lines 818-829 |
| Novelty code at lines 841-859 | Lines 846-864 |
| `get_recommendation_weights` at lines 89-142 | Lines 89-140 (close, but docstring through return) |
| Scoring formula at lines 877-882 | Lines 882-887 |
| `apply_feedback_learning` at lines 254-317 | Line 254 is correct; function ends at 324 |

The `_build_gem_explanation` citation (`views.py, lines 1037-1092`) is accurate.

For a portfolio project used in interviews, stale line numbers undermine credibility when an interviewer opens the source file. The discrepancy for `_cosine_similarity` (claims 813-824, actual 818-829) is the largest and most likely to be checked.

**Fix:** Update all source comment line references to match the current file. Verify with `grep -n "def _cosine_similarity\|def _score_recommendations"` before committing.

---

## Info

### IN-01: `_build_gem_explanation` described as returning "four sentence shapes" but function has three sentence shapes plus one fallback

**File:** `CONCEPTS.md:397,419,449`

**Issue:** CONCEPTS.md states in two places that the function returns "one of **four** fixed sentence templates" (lines 397 and 449). The actual function logic has three sentence branches (dominant == `genre_sim`, `novelty`, or `feedback_multiplier`) plus one early-return fallback for empty/all-zero breakdowns. Calling the fallback a "sentence template" conflates an edge-case guard with a normal template. SYSTEM_DESIGN.md Data Flow step 9 (line 244) correctly describes this as "one of four templates."

The description is not meaningfully wrong — the fallback does produce a sentence — but "three branches that each call a template, plus one zero-breakdown fallback" is more precise.

**Fix:** Change "fills one of four fixed sentence templates" to "returns one of three domain-specific sentences or a neutral fallback string when all scoring components are zero" for precision.

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

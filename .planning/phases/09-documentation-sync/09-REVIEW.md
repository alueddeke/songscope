---
phase: 09-documentation-sync
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - CONCEPTS.md
  - SYSTEM_DESIGN.md
findings:
  critical: 4
  warning: 4
  info: 1
  total: 9
status: issues_found
---

# Phase 09: Code Review Report — Documentation Sync

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Both documentation files were reviewed against the live source code in `backend/apps/recommendations/hybrid_recommendation_engine.py`, `backend/apps/recommendations/personalization_engine.py`, and `backend/apps/core/views.py`.

The docs are generally well-structured and cover the right concepts. However, four factual claims directly contradict live code behavior, which would cause an interviewer or engineer who reads the code to lose trust in both documents. Three of these are about Thompson Sampling — the normalization method, the code snippet, and the SYSTEM_DESIGN description — all describe sum-normalization when the actual code uses max-normalization. The fourth is about `get_daily_gem` returning an empty `score_breakdown` for cached gems, when the code actually returns the persisted value.

There are also four warnings: missing documentation of the taste-vector cap, stale template strings for `_build_gem_explanation`, a missing strategy in the five-source list, and an incorrect inline description in the `get_daily_gem` docstring inside `views.py` that SYSTEM_DESIGN.md echoes.

---

## Critical Issues

### CR-01: Thompson Sampling normalization is documented as sum-to-1 but code uses max-normalization

**File:** `CONCEPTS.md:119-121`

**Issue:** The formula section states:
```
normalized weight_i = theta_i / sum(theta_j)
```
And the embedded code snippet (lines 148–174 of CONCEPTS.md) shows `result = {k: v / total for k, v in thetas.items()}` — sum normalization. The actual code at `hybrid_recommendation_engine.py:137-138` is:
```python
max_weight = max(thetas.values()) or 1.0
result = {k: v / max_weight for k, v in thetas.items()}
```
This is max-normalization (best source gets weight 1.0, all others get < 1.0). Sum-normalization would produce weights around 0.2 each, which the code's own comment at line 133 explicitly rejects as incorrect behavior ("penalizing warm sources relative to the cold-start 1.0 baseline"). The two normalizations have different semantics: max-normalization is a multiplier capped at 1.0; sum-normalization would dampen all sources together.

**Fix:** Update the formula block and embedded code snippet in CONCEPTS.md:
```
max_theta = max(theta_i for all i)
weight_i = theta_i / max_theta        (best source → 1.0 multiplier; others scaled proportionally)
```
Replace the code snippet to match the actual implementation at lines 133–140 of `hybrid_recommendation_engine.py`.

---

### CR-02: Thompson Sampling formula claims "selected source = argmax" but the bandit weights ALL sources

**File:** `CONCEPTS.md:117-119`

**Issue:** The formula block states:
```
theta_i ~ Beta(s_i + 1, f_i + 1)   for each source i
selected source = argmax_i(theta_i)
normalized weight_i = theta_i / sum(theta_j)
```
The claim "selected source = argmax" implies a single source is chosen per request (winner-take-all). The actual behavior is different: `get_recommendation_weights()` returns a weight for every source, and `_score_recommendations()` at line 887 applies each source's weight as a post-score multiplier to every candidate from that source. No single source is selected; all five receive a weight between 0 and 1 that scales their candidates' scores. The "argmax" line is factually wrong and misrepresents the architecture.

**Fix:** Replace the formula block to accurately describe the weight-multiplier approach:
```
theta_i ~ Beta(s_i + 1, f_i + 1)   for each source i
weight_i = theta_i / max_j(theta_j)          (all sources weighted; best source gets 1.0)
final_score(candidate) = base_score * weight_source(candidate)
```

---

### CR-03: `_build_gem_explanation` sentence templates in CONCEPTS.md do not match actual code

**File:** `CONCEPTS.md:403-413`

**Issue:** CONCEPTS.md documents these four sentence templates:
```
"We think you'll love {track} by {artist} — it matches your taste in {source} tracks."
"{track} by {artist} is a hidden gem — popular enough to be good, underground enough to feel like a find."
"You've liked {artist} before, so {track} seemed like a natural next pick."
(fallback): "{track} by {artist} scored well across all three dimensions — genre fit, novelty, and your feedback history."
```
The actual templates in `views.py:1077-1092` are:
```python
# genre_sim dominant:
f'Matches your listening taste — genre similarity: {pct}%, discovered {source_str}'
# novelty dominant:
'A hidden gem — low popularity score makes it a genuine discovery, found {source_str}'
# feedback_multiplier dominant:
f"You've liked {artist_name} before — that feedback boosted this pick, sourced {source_str}"
# fallback (empty/zero breakdown):
'Picked based on your listening patterns'
```
The documented templates are entirely different from the actual strings. The genre-sim template additionally includes a numeric percentage that is absent from the documented version. The fallback template documented ("scored well across all three dimensions") does not exist in the code; the actual fallback is a single neutral sentence used only when `breakdown` is empty or all-zero. An interviewer who reads the code after reviewing these docs would immediately identify the discrepancy.

**Fix:** Replace the four template strings in CONCEPTS.md with the actual strings from `views.py:1077-1092`.

---

### CR-04: SYSTEM_DESIGN.md claims cached `get_daily_gem` returns `score_breakdown: {}` — it returns the persisted value

**File:** `SYSTEM_DESIGN.md:138-139`

**Issue:** The ScoreBreakdown component invariant states:
> "`score_breakdown` is returned in the `GET /api/daily-gem/` response for both cached and fresh gems. For cached gems it is read from the persisted `DailyGem.score_breakdown` column"

This is internally inconsistent with the inline `get_daily_gem` view docstring at `views.py:1101-1102`, which says "returns it immediately with `score_breakdown: {}`". The *actual* cached branch code at `views.py:1131` returns `'score_breakdown': gem.score_breakdown`, which is the persisted JSONField value — not an empty dict.

However, SYSTEM_DESIGN.md's ScoreBreakdown invariants correctly state the cached path reads from the persisted column. The problem is that the phrase "with `score_breakdown: {}`" is embedded in the view docstring inside `views.py` (not in SYSTEM_DESIGN.md directly) and SYSTEM_DESIGN.md's Data Flow section at step 10 says "the response to the frontend includes the `score_breakdown` dict" without distinguishing cached vs. fresh. The SYSTEM_DESIGN.md claim is ambiguous but the invariant block has the correct version. The larger risk is that the view's own docstring is wrong and could mislead future maintainers.

**Fix:** Remove the "(we don't re-score cached gems)" note from `views.py:1102` and clarify it returns the persisted `score_breakdown`. In SYSTEM_DESIGN.md, ensure the Data Flow step 10 explicitly states the cached branch also returns the persisted `score_breakdown` (not `{}`).

---

## Warnings

### WR-01: CONCEPTS.md Online Learning formula omits the `TASTE_VECTOR_MAX = 5.0` cap on LIKE updates

**File:** `CONCEPTS.md:191-203`

**Issue:** The documented SGD formula shows:
```
taste_vector[g] := taste_vector[g] + lr * signal
```
And the dislike clamp is documented (`max(0.0, ...)`), but the like path is shown as unbounded. The actual code at `personalization_engine.py:287-290` applies:
```python
TASTE_VECTOR_MAX = 5.0
taste_vector[genre] = min(taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR, TASTE_VECTOR_MAX)
```
The cap prevents unbounded weight growth from repeated like/unlike cycles. This changes the algorithmic behavior: after 50 likes of the same genre, the taste vector is capped at 5.0 rather than 5.0 — which happens to be the same here — but more importantly, users cannot unlike their way below 0 and re-like back above the cap indefinitely. The cap is a design constraint that should be documented because it affects how interviewers evaluate the online learning claim.

**Fix:** Add a line to the formula block:
```
LIKE update is clamped above: taste_vector[g] = min(taste_vector[g] + lr, TASTE_VECTOR_MAX)
where TASTE_VECTOR_MAX = 5.0
```
Also add a brief note in the Implementation Note paragraph explaining the cap and its rationale.

---

### WR-02: SYSTEM_DESIGN.md and CONCEPTS.md list `genre_search` as a strategy — it exists in `SOURCE_DEFAULTS` but is never called in `get_recommendations()`

**File:** `SYSTEM_DESIGN.md:148-153` and `CONCEPTS.md:108`

**Issue:** Both documents describe five candidate sources: `playlist_mining`, `artist_network`, `genre_search`, `related_artists`, `contextual`. The `SOURCE_DEFAULTS` constant in the engine confirms these five keys. However, `get_recommendations()` at lines 182–206 calls only:
- Strategy 1: `_get_playlist_recommendations` (playlist_mining)
- Strategy 2: `_get_artist_network_recommendations` (artist_network)
- Strategy 3: `_get_contextual_recommendations` (contextual)
- Strategy 5: `_get_related_artist_recommendations` (related_artists)

There is no Strategy 4 and no call to any `genre_search` method. The source label `genre_search` in `SOURCE_DEFAULTS` is never assigned to any candidate's `source` field during normal operation. This means Thompson Sampling accumulates no `source_stats` for `genre_search`, and CONCEPTS.md's claim that the system "generates candidates from five distinct sources" is factually incorrect — it uses four.

**Fix:** In both documents, update the source list to reflect four active strategies. Note that `genre_search` is reserved in `SOURCE_DEFAULTS` but not yet implemented in `get_recommendations()`.

---

### WR-03: SYSTEM_DESIGN.md Feedback Loop description says taste-vector update is skipped when no genre data, but bandit still fires — this is only partially correct

**File:** `SYSTEM_DESIGN.md:187-189`

**Issue:** The Feedback Loop invariants state:
> "If the track has no genre data, the taste-vector update is skipped (logged as a warning); the bandit update still fires if the source is known."

The actual code at `personalization_engine.py:268-275` returns early when genres are empty:
```python
if not genres:
    logger.warning(...)
    return
```
The `return` at line 275 exits `apply_feedback_learning` before the bandit update code at lines 305-316. The bandit update does NOT fire when genre data is absent — the entire function returns early. The SYSTEM_DESIGN.md claim that "the bandit update still fires" is incorrect.

**Fix:** Update the invariant to:
> "If the track has no genre data, both the taste-vector update and the bandit update are skipped (function returns early after logging a warning). Both updates require non-empty genre lists."

---

### WR-04: SYSTEM_DESIGN.md Feedback Loop description says Thompson Sampling normalization is "normalized to sum to 1.0"

**File:** `SYSTEM_DESIGN.md:181`

**Issue:** The Scoring & Ranking section key invariants state:
> "Weights (0.4, 0.3, 0.3) are locked — not tunable via API or user preference."
> "`genre_sim` is cosine similarity between candidate artist genres and `UserProfile.data['taste_vector']`."

These are accurate. However, the `get_recommendation_weights()` docstring comment at `hybrid_recommendation_engine.py:104` — which SYSTEM_DESIGN.md implicitly describes — says "normalized to sum to 1.0" in the method's own docstring, while the code normalizes to max=1.0. This mirrors CR-01 and WR is appropriate here because SYSTEM_DESIGN.md's Scoring & Ranking section references source weights as multipliers without specifying the normalization method, which is ambiguous but not outright false. The companion Feedback Loop section at line 181 also does not describe the normalization, so there is no direct false claim — but the Thompson Sampling method's behavior needs to be clear in SYSTEM_DESIGN.md for an accurate architecture description.

**Fix:** In SYSTEM_DESIGN.md's Recommendation Engine component description, add a clarifying note that the Thompson Sampling source weights are normalized so the best-performing source receives a 1.0 multiplier (max-normalization), not sum-to-1.0.

---

## Info

### IN-01: CONCEPTS.md references `INTERVIEW_PREP_SONGSCOPE.md` — verify this file exists

**File:** `CONCEPTS.md:3` and `CONCEPTS.md:469`

**Issue:** Both the opening paragraph and the Further Reading section link to `INTERVIEW_PREP_SONGSCOPE.md`. This file is referenced as the primary interview Q&A companion document. If the file does not exist or is not in the root directory, the cross-reference is broken and the main documentation flow is interrupted.

**Fix:** Confirm the file exists at the project root. If it does not, either remove the links or create the file.

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

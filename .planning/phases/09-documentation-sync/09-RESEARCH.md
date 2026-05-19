# Phase 9: Documentation Sync — Research

**Researched:** 2026-05-19
**Domain:** Technical documentation audit (CONCEPTS.md, SYSTEM_DESIGN.md) against v1.1 implementation
**Confidence:** HIGH — all findings verified directly against source files

---

## Summary

Phase 9 is a documentation-only phase. No new code is written; both CONCEPTS.md and SYSTEM_DESIGN.md
are updated to reflect v1.1 changes shipped across phases 6, 7, and 8. The research task was to read
the existing docs and every relevant source file, then produce an exhaustive gap table the planner can
translate directly into edit instructions.

Six concrete gaps were identified across the two documents. The docs are structurally sound; no sections
need to be deleted or reorganised — every v1.1 concept has a natural home in the existing structure.
The most complex addition is the `_build_gem_explanation` data-flow description for SYSTEM_DESIGN.md;
everything else is a table update or an appended paragraph.

**Primary recommendation:** Two thin task files — one per document — each containing precise
before/after edit instructions. No architectural decisions are required; every fact is locked in
the source code.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Documentation editing | File system (static docs) | — | Pure text authoring, no runtime tier involved |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | CONCEPTS.md updated | Six gaps identified; two of the six land in CONCEPTS.md (compound hit rate, explanation determinism) |
| DOCS-02 | SYSTEM_DESIGN.md updated | Four of the six gaps land in SYSTEM_DESIGN.md (DailyGem field table, _build_gem_explanation data flow, add_track_to_liked side effect, Score Breakdown API) |
</phase_requirements>

---

## Gap Table — Complete

Each row is one discrete documentation gap. "Current state" is what the doc says today; "What to write"
is the verified correct content.

| # | Doc | Gap | Current State | What to Write | Source Evidence |
|---|-----|-----|---------------|---------------|-----------------|
| G-01 | CONCEPTS.md | `compound_hit_rate` definition with OR-semantics rationale | Section "Recommendation Evaluation Metrics" mentions `gem_acceptance_rate` and `hidden_gem_rate` but has no mention of `compound_hit_rate` | New paragraph in "Recommendation Evaluation Metrics": define `compound_hit_rate = (was_liked IS TRUE OR was_saved IS TRUE) / gem_total`. Explain why OR-semantics: a save without a like still signals value; using strict `was_liked` would under-count positive engagement. Note that `None` counts as a miss (identity check, not truthiness). | `backend/apps/core/views.py` lines 425-428 |
| G-02 | CONCEPTS.md | Explanation is deterministic, not OpenAI | No mention anywhere; an interviewer could reasonably assume AI generates explanations | New paragraph in or after "Compound Success Metric" (or a standalone subsection): the `explanation` field on `DailyGem` is produced by `_build_gem_explanation()`, a pure function with no external calls. It reads the three `score_breakdown` components (genre_sim, novelty, feedback_multiplier), identifies the dominant one, and fills a fixed sentence template. No LLM, no API call, no randomness — same breakdown always produces the same sentence. | `backend/apps/core/views.py` lines 1037-1092 |
| G-03 | SYSTEM_DESIGN.md | `DailyGem` field table is missing four v1.1 columns | Persistence Layer table shows 5 fields for DailyGem: `user`, `track`, `date`, `was_liked`, `track_popularity` | Add four rows: `score_breakdown` (JSONField, default={}), `score_total` (FloatField, nullable), `was_saved` (BooleanField, nullable), `taste_vector_snapshot` (JSONField, nullable). Note purpose of each (see below). Also note `was_skipped` (BooleanField, default=False) which exists in the model but is not yet wired to any view — flag as future. | `backend/apps/core/models.py` lines 290-293 |
| G-04 | SYSTEM_DESIGN.md | `_build_gem_explanation` data flow description | Data flow section (steps 1-13) and Component Descriptions have no mention of `_build_gem_explanation` | Add to "Data Flow: Daily Gem Request" step 9 (or as a new step between 8 and 9): after the top candidate is selected, `_build_gem_explanation(breakdown, track_name, artist_name, source)` is called. It inspects the three score_breakdown keys, picks the dominant component, and fills a sentence template — no external calls. The result is stored as `DailyGem.explanation`. Add a brief Component Description entry for `_build_gem_explanation`. | `backend/apps/core/views.py` lines 1037-1092, 1176-1182 |
| G-05 | SYSTEM_DESIGN.md | `add_track_to_liked` sets `was_saved=True` side-effect | API Surface table lists `add_track_to_liked` with purpose "Save track to Spotify liked songs" — no mention of the DB side-effect | Extend the purpose cell or add a Key Invariants note: after calling `sp.current_user_saved_tracks_add()`, the view calls `DailyGem.objects.filter(user, date=today, track__spotify_id=track_id).update(was_saved=True)`. This means `was_saved` can become True independently of `was_liked`, enabling the OR-semantics in `compound_hit_rate`. | `backend/apps/core/views.py` lines 850-856 |
| G-06 | SYSTEM_DESIGN.md | Score Breakdown API contract | No mention of `score_breakdown` field in the API Surface table or the `GET /api/daily-gem/` description | Add to the "Data Flow" description and/or API Surface table: `GET /api/daily-gem/` now returns a `score_breakdown` field — a dict with keys `genre_sim` (float), `novelty` (float), `feedback_multiplier` (float), and `source` (str). For cached gems, `score_breakdown` is returned from the persisted `DailyGem.score_breakdown` column. For fresh gems, it comes from `_score_recommendations()` and is also written to the DB. Add `ScoreBreakdown` frontend component to Component Descriptions. | `backend/apps/core/views.py` lines 1118-1133, 1210-1224; `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` |

---

## Source Evidence Detail

### `score_breakdown` structure (verified)

```python
# backend/apps/recommendations/hybrid_recommendation_engine.py, lines 875-880
rec['score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'source': rec.get('source', ''),
}
```

[VERIFIED: backend/apps/recommendations/hybrid_recommendation_engine.py:875]

### `DailyGem` model fields (verified)

```python
# backend/apps/core/models.py, lines 280-302
class DailyGem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    explanation = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    preview_url = models.URLField(max_length=500, blank=True)
    track_popularity = models.IntegerField(default=0)
    was_liked = models.BooleanField(null=True, blank=True)
    score_breakdown = models.JSONField(default=dict, blank=True)   # v1.1
    score_total = models.FloatField(null=True, blank=True)         # v1.1
    was_saved = models.BooleanField(null=True, blank=True)         # v1.1
    taste_vector_snapshot = models.JSONField(null=True, blank=True)# v1.1
    was_skipped = models.BooleanField(default=False)               # exists, not yet wired
    created_at = models.DateTimeField(auto_now_add=True)
```

[VERIFIED: backend/apps/core/models.py:280-302]

### `compound_hit_rate` logic (verified)

```python
# backend/apps/core/views.py, lines 425-428
compound_hits = sum(
    1 for g in gem_list
    if g['was_liked'] is True or g['was_saved'] is True
)
compound_hit_rate = compound_hits / gem_total
```

[VERIFIED: backend/apps/core/views.py:425-428]

`None` is excluded because Python's `is True` identity check — `None is True` is `False`.

### `_build_gem_explanation` (verified, deterministic pure function)

```python
# backend/apps/core/views.py, lines 1037-1092
def _build_gem_explanation(breakdown, track_name, artist_name, source) -> str:
    """
    Pure function: no external calls, no logging, no exceptions on any reasonable input.
    Returns one of four sentence shapes based on the dominant scoring component.
    """
    ...
    dominant = max(components, key=components.get)
    # Three fixed sentence templates — no LLM
```

[VERIFIED: backend/apps/core/views.py:1037-1092]

### `add_track_to_liked` sets `was_saved` (verified)

```python
# backend/apps/core/views.py, lines 850-856
DailyGem.objects.filter(
    user=request.user, date=today, track__spotify_id=track_id
).update(was_saved=True)
```

[VERIFIED: backend/apps/core/views.py:850-856]

### `ScoreBreakdown` frontend component (verified)

Keys displayed: `genre_sim` (label "Genre Match"), `novelty` (label "Novelty"), `feedback_multiplier`
(label "Feedback"). Each bar is `Math.round(raw * 100 / 5) * 5` — rounded to nearest 5%.

[VERIFIED: frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx:7-11]

### `compound_hit_rate` in MetricsStrip (verified)

The frontend reads `metrics.compound_hit_rate` and displays it as "Hit rate".

[VERIFIED: frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:57-60]

---

## Recommended Section Placement

### CONCEPTS.md

| Gap | Insert location |
|-----|----------------|
| G-01 (`compound_hit_rate`) | Inside existing "Recommendation Evaluation Metrics" section, after the current `precision@k` paragraph — this is where the metric family lives |
| G-02 (deterministic explanation) | New subsection after "Compound Success Metric" — title suggestion: "Gem Explanation (Template-Based)" or fold into an existing section as a sub-heading |

The TOC at the top of CONCEPTS.md will need one new entry if G-02 becomes a full section.

### SYSTEM_DESIGN.md

| Gap | Insert location |
|-----|----------------|
| G-03 (DailyGem field table) | "Persistence Layer" table — add 4 rows to DailyGem row |
| G-04 (`_build_gem_explanation` data flow) | "Data Flow: Daily Gem Request" step 9 (between scoring and response); add minimal Component Description |
| G-05 (`add_track_to_liked` side-effect) | API Surface table, purpose cell for `POST /api/add-track-to-liked/`; and/or a Key Invariants paragraph after the table |
| G-06 (Score Breakdown API contract) | "Data Flow: Daily Gem Request" response description; add `ScoreBreakdown` to Component Descriptions list |

The Architecture Diagram mermaid block should also add `ScoreBreakdown[ScoreBreakdown]` inside the
Frontend subgraph, connected to `DailyGemUI`.

---

## Stale Content to Correct

One existing entry in SYSTEM_DESIGN.md is now inaccurate:

**Persistence Layer table — DailyGem row** (line 185)

Current:
```
| `DailyGem` | `user`, `track`, `date`, `was_liked`, `track_popularity` | One gem per user per day; source of truth for metrics |
```

Correct after G-03: the Key fields cell must list all 9 substantive fields (existing 5 + 4 new v1.1).

No other existing prose is factually wrong — the stale Metrics endpoint description at line 318 in
CONCEPTS.md (`gem_acceptance_rate → precision@1`) remains correct; `compound_hit_rate` is an addition,
not a replacement.

---

## Complexity Estimate

**One plan per document is the right split** — the two documents are independent files edited by
different wave tasks. Interleaving edits to both in a single plan would make rollback harder.

Suggested plan structure:

```
09-01-PLAN.md   Wave 1: Update CONCEPTS.md (G-01, G-02)
09-02-PLAN.md   Wave 2: Update SYSTEM_DESIGN.md (G-03, G-04, G-05, G-06)
```

Each wave is small — estimated 1-2 hours of editing for a careful human; straightforward for an
executor. The plans can be merged into a single plan file with two waves if the team prefers.

---

## Common Pitfalls

### Pitfall 1: Confusing `compound_hit_rate` with `gem_acceptance_rate`
**What goes wrong:** Writer describes `compound_hit_rate` as "an alias for acceptance rate."
**Why:** They look similar — both divide a hit count by `gem_total`.
**Correct:** `gem_acceptance_rate` requires `was_liked IS True`. `compound_hit_rate` uses
`was_liked IS True OR was_saved IS True`. A user who saves but does not like contributes to
`compound_hit_rate` but not `gem_acceptance_rate`.

### Pitfall 2: Calling the explanation "AI-generated"
**What goes wrong:** Doc says something like "the AI explanation" or "LLM-generated insight."
**Why:** The field is called `explanation` and the system does use OpenAI in other paths (AIFeedback).
**Correct:** `_build_gem_explanation` is a pure Python function — three `if` branches, three sentence
templates, no network call.

### Pitfall 3: Omitting `taste_vector_snapshot` purpose
**What goes wrong:** It's listed as a field but its purpose isn't explained, leaving readers confused.
**Correct:** It stores a copy of the user's `taste_vector` at the moment the gem is generated.
Purpose: offline evaluation — you can later compare what the model "knew" at recommendation time
against the user's eventual feedback, without needing to reconstruct historical taste-vector states.

### Pitfall 4: Forgetting `was_skipped` in the field table
**What goes wrong:** Researcher reads model and lists only 4 new v1.1 fields; misses `was_skipped`.
**Correct:** `was_skipped = BooleanField(default=False)` exists in the model (line 294) but is not
wired to any view yet. The field table update should list it with a note: "not yet wired — reserved
for future skip-signal feedback loop."

---

## Environment Availability

Step 2.6: SKIPPED — this phase contains only document edits; no external tools, runtimes, or services
are required.

---

## Validation Architecture

Step 2.4: No automated tests cover documentation content. Validation is manual review against the
success criteria defined in the phase:

| Success Criterion | How to Verify |
|-------------------|---------------|
| `compound_hit_rate` definition with OR-semantics rationale | Read CONCEPTS.md "Recommendation Evaluation Metrics" — formula and None-identity rationale present |
| `taste_vector_snapshot` purpose (offline evaluation) | Read SYSTEM_DESIGN.md Persistence Layer table — purpose column explains offline eval |
| Score breakdown persistence rationale | Read SYSTEM_DESIGN.md — explains `score_breakdown` written at gem creation, not re-derived on read |
| Explanation is deterministic | Read CONCEPTS.md new section — states "pure function, no external calls, fixed templates" |
| DailyGem field table complete | Count fields in Persistence Layer table — should have 9 DailyGem fields |
| `_build_gem_explanation` data flow | Read "Data Flow: Daily Gem Request" — step describes helper call and output |
| `add_track_to_liked` `was_saved` side-effect | Read API Surface entry or Key Invariants — `was_saved=True` update noted |
| Score Breakdown API contract | Read `GET /api/daily-gem/` response description — `score_breakdown` dict structure documented |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `was_skipped` is not yet wired to any view | Pitfall 4, G-03 | If it is wired somewhere not checked, the "reserved" note would be inaccurate. Mitigated: grep found no view referencing `was_skipped` | 

All other claims in this research were verified against source files — no user confirmation needed.

---

## Open Questions

None. All success criteria map to verified source code.

---

## Sources

### Primary (HIGH confidence)

- `backend/apps/core/models.py` lines 280-302 — DailyGem model field definitions
- `backend/apps/core/views.py` lines 425-428 — compound_hit_rate computation
- `backend/apps/core/views.py` lines 1037-1092 — `_build_gem_explanation` full implementation
- `backend/apps/core/views.py` lines 850-856 — `add_track_to_liked` `was_saved` update
- `backend/apps/core/views.py` lines 1095-1228 — `get_daily_gem` response shape including `score_breakdown`
- `backend/apps/recommendations/hybrid_recommendation_engine.py` lines 875-880 — `score_breakdown` dict structure
- `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` — row labels and bar formula
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — `compound_hit_rate` display as "Hit rate"
- `/Users/antonilueddeke/Desktop/Projects/songscope/CONCEPTS.md` — current state, 394 lines
- `/Users/antonilueddeke/Desktop/Projects/songscope/SYSTEM_DESIGN.md` — current state, 255 lines

---

## Metadata

**Confidence breakdown:**
- Gap identification: HIGH — every gap verified by direct file read
- Source evidence: HIGH — line numbers cited from actual source
- Section placement: HIGH — based on reading existing doc structure
- Pitfalls: HIGH — based on reading actual code semantics

**Research date:** 2026-05-19
**Valid until:** Stable indefinitely — this is a one-time sync, no moving targets

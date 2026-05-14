# Phase 7: Backend Wiring - Research

**Researched:** 2026-05-14
**Domain:** Django ORM wiring, view-layer score persistence, deterministic explanation generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Explanation Text Format (_build_gem_explanation)**
- D-01: Pure function signature: `_build_gem_explanation(breakdown: dict, track_name: str, artist_name: str, source: str) -> str` — no OpenAI, no external calls, deterministic from score components.
- D-02: Dominant signal = genre_sim: sentence is genre-forward with % exposed — e.g., `"Matches your indie rock taste — genre similarity: 82%, discovered via playlist mining"`. Exposes cosine similarity component directly.
- D-03: Dominant signal = novelty: discovery angle — e.g., `"A hidden gem — low popularity score makes it a genuine discovery, found via artist network"`.
- D-04: Dominant signal = feedback_multiplier: feedback-forward — e.g., `"You've liked [artist] before — that feedback boosted this pick, sourced from related artists"`.
- D-05: Source strategy is always appended (e.g., "via playlist mining", "via artist network", "via contextual discovery", "via related artists", "via fallback").
- D-06: Dominant component = whichever of `genre_sim`, `novelty`, `feedback_multiplier` has the highest value in `breakdown`. If breakdown is empty or all zeros, fall back to: `"Picked based on your listening patterns"`.

**was_saved Wiring**
- D-07: After a successful `sp.current_user_saved_tracks_add([track_id])`, find today's DailyGem for this user with matching `track__spotify_id=track_id`: `DailyGem.objects.filter(user=..., date=today, track__spotify_id=track_id).update(was_saved=True)`.
- D-08: If no matching DailyGem is found, silent no-op — `was_saved` stays null. No error, no log. Spotify save still returns 200.
- D-09: Failure to write `was_saved` must never 500 the save action — wrap in try/except, return success regardless.

**Score Persistence Location**
- D-10: All 4 fields (`score_breakdown`, `score_total`, `explanation`, `taste_vector_snapshot`) written as `defaults={...}` inside `get_or_create` in `get_daily_gem` (single DB write).
- D-11: Cached branch fix: replace `'score_breakdown': {}` with `'score_breakdown': gem.score_breakdown` and `'explanation': gem.explanation` at all 3 cached return sites (~lines 1060, 1123). Read directly from gem object — no extra DB round-trip.

**Compound Hit Rate**
- D-12: Denominator = `DailyGem.objects.filter(user=...).count()` — all gems, nulls count as misses. Formula: `hits = gems where was_liked=True OR was_saved=True; rate = hits / total`.
- D-13: Add `compound_hit_rate` to the JSON response of `get_recommendation_metrics` alongside `gem_acceptance_rate`. Use 0.0 as default when total is 0.

### Claude's Discretion
- Exact helper function placement (`_build_gem_explanation` as module-level in `views.py` or in a utils module — follow existing patterns)
- Test class naming and organization (follow `TestDailyGemWasLikedSync` pattern)
- Genre name extraction from `score_breakdown` — if `genre_sim` is dominant but no genre name is available, use `"your listening taste"` as placeholder

### Deferred Ideas (OUT OF SCOPE)
- Backfilling `was_saved` for historical gems via Spotify saved-tracks API
- Rolling window for `compound_hit_rate` (e.g., last 7 days) — deferred to Phase 8/evaluation dashboard
- Model-level `compound_hit` property on `DailyGem` — not needed for Phase 7; compute inline in the metrics view
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHEMA-02 | HybridRecommendationEngine writes `score_breakdown` dict and `score_total` float into `DailyGem` at creation time (fresh-generation branch) | `_score_recommendations` already produces both; `get_or_create` `defaults` dict needs to include them from `gem_data['score_breakdown']` and `gem_data['score']` |
| SCHEMA-03 | `taste_vector_snapshot` captured from `UserProfile.data['taste_vector']` at recommendation time and persisted to `DailyGem` | `engine.profile.data.get('taste_vector', {})` is already available on the engine object at the point of `get_or_create` |
| SCHEMA-04 | All 3 return sites in `get_daily_gem` return persisted `score_breakdown` from DB instead of hardcoded `{}` | Lines 1060, 1123 return `{}` today; the gem object is already in scope at both sites — direct field read |
| EXPLAIN-01 | `_build_gem_explanation(breakdown, track_name, artist_name) -> str` pure function | All inputs available at creation time; no imports needed beyond stdlib |
| EXPLAIN-02 | `DailyGem.explanation` populated at creation time via `_build_gem_explanation` | `explanation` field already exists in model and is in `defaults={}` dict; replace `''` with function call |
| METRIC-02 | `compound_hit_rate` (`was_liked OR was_saved`) computed and exposed in `/api/recommendation-metrics/` endpoint | `was_saved` and `was_liked` fields both exist on DailyGem; formula mirrors `gem_acceptance_rate` pattern already in `get_recommendation_metrics` |
</phase_requirements>

---

## Summary

Phase 7 is a pure wiring phase — no new models, no migrations, no new dependencies. Every capability it needs already exists in the codebase. The `_score_recommendations` method already produces `score_breakdown` dict and `score` float on each candidate. The `DailyGem` model already has `score_breakdown`, `score_total`, `was_saved`, `taste_vector_snapshot`, and `explanation` fields (migration 0008 from Phase 6). The view already calls `get_or_create` with a `defaults` dict at line 1095. The compound metric formula exactly mirrors the existing `gem_acceptance_rate` pattern at line 424.

The work is four targeted edits in `views.py`: (1) expand the `get_or_create` defaults dict to include the 4 score fields, calling the new `_build_gem_explanation` helper inline; (2) fix the 2 cached-branch `'score_breakdown': {}` literals to read `gem.score_breakdown`; (3) add a non-fatal `was_saved` update in `add_track_to_liked` after the Spotify save call; (4) add `compound_hit_rate` to the `get_recommendation_metrics` response alongside the existing `gem_acceptance_rate`. No engine changes are needed. No frontend changes are in scope.

The test infrastructure is already standing — 46 tests pass across the affected test files. New tests follow three existing patterns: `TestDailyGemWasLikedSync` (ORM round-trip), `TestGetDailyGemCached` (view-level mock), and `TestMetricsEndpoint` (DB + endpoint).

**Primary recommendation:** All 4 wiring changes land in `views.py`. Write `_build_gem_explanation` as a module-level private function in that file (no utils module needed — no existing helpers live outside views.py in the core app). Commit in a single plan.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Score persistence at creation | API / Backend (views.py) | Database (DailyGem) | Score data flows from engine -> view -> DB; ORM write in fresh branch |
| Explanation generation | API / Backend (views.py helper) | — | Pure deterministic function; no external calls; belongs with the data it consumes |
| Cached branch score read | API / Backend (views.py) | — | `gem` object already in memory; direct field access |
| was_saved wiring | API / Backend (views.py) | Database (DailyGem) | Non-fatal ORM update after Spotify API call in same view |
| Compound hit rate | API / Backend (views.py) | Database (DailyGem) | Inline query in metrics view; matches existing gem_acceptance_rate pattern |

---

## Standard Stack

### Core (verified from codebase inspection)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | (project version) | `get_or_create`, `filter().update()`, `save(update_fields=[...])` | Already used pervasively in views.py and tests |
| DRF `api_view` / `permission_classes` | (project version) | View decorators — no change needed | All affected views already decorated |
| Python stdlib | 3.11 | `max()` with key for dominant component in `_build_gem_explanation` | Zero new imports |

No new packages to install. [VERIFIED: codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP GET /api/daily-gem/
       |
       v
  get_daily_gem()
       |
  [Cached branch] ---------> DailyGem.objects.get()
       |                              |
       |                      gem object in scope
       |                              |
       |                    gem.score_breakdown  <-- READ from DB (fix)
       |                    gem.explanation      <-- READ from DB (fix)
       |                              |
       |                      JsonResponse (cached=True)
       |
  [Fresh branch]
       |
  HybridRecommendationEngine.get_recommendations()
       |
  _score_recommendations()  -->  candidates[0] has score_breakdown + score
       |
  engine.profile.data['taste_vector']  -->  taste_vector_snapshot
       |
  _build_gem_explanation(breakdown, track_name, artist_name, source)
       |
  DailyGem.objects.get_or_create(
      defaults={
          score_breakdown, score_total, explanation,
          taste_vector_snapshot, ...
      }
  )
       |
  JsonResponse (cached=False, score_breakdown populated)

HTTP POST /api/add-track-to-liked/
       |
  add_track_to_liked()
       |
  sp.current_user_saved_tracks_add([track_id])  -- SUCCESS
       |
  [try/except non-fatal]
  DailyGem.objects.filter(user, date=today, track__spotify_id=track_id)
                   .update(was_saved=True)
       |
  JsonResponse({'message': 'all good'})

HTTP GET /api/recommendation-metrics/
       |
  get_recommendation_metrics()
       |
  gems = DailyGem.objects.filter(user=user)
       |
  compound_hits = count(was_liked=True OR was_saved=True)
  compound_hit_rate = hits / total  (0.0 if total == 0)
       |
  JsonResponse({..., 'compound_hit_rate': compound_hit_rate})
```

### Recommended Project Structure

No structural changes. All edits land in:

```
backend/
├── apps/core/
│   └── views.py          # All 4 wiring changes + _build_gem_explanation helper
└── tests/
    ├── test_feedback.py              # Extend for was_saved wiring
    ├── test_views_gem_feedback.py    # Extend for cached branch score_breakdown
    └── test_metrics.py              # Extend for compound_hit_rate
```

### Pattern 1: Expanding get_or_create defaults (SCHEMA-02, SCHEMA-03, EXPLAIN-02)

**What:** Add 4 new fields to the `defaults` dict in the existing `DailyGem.objects.get_or_create` call.
**When to use:** This is the single correct write point — the row is created once; all score data is available in scope at this line.

```python
# Source: [VERIFIED: views.py line 1095 — existing pattern]
gem_data = candidates[0]
taste_snapshot = engine.profile.data.get('taste_vector', {})
breakdown = gem_data.get('score_breakdown', {})
source = breakdown.get('source', '')

gem, created = DailyGem.objects.get_or_create(
    user=request.user,
    date=today,
    defaults={
        'track': track_obj,
        'explanation': _build_gem_explanation(
            breakdown, gem_data.get('name', ''), gem_data.get('artist', ''), source
        ),
        'image_url': gem_data.get('image_url') or '',
        'preview_url': gem_data.get('preview_url') or '',
        'track_popularity': gem_data.get('popularity', 0),
        'score_breakdown': breakdown,
        'score_total': gem_data.get('score', None),
        'taste_vector_snapshot': taste_snapshot,
    },
)
```

### Pattern 2: Cached-branch fix (SCHEMA-04)

**What:** Replace the 2 hardcoded `'score_breakdown': {}` literals with reads from the gem object that is already in scope.
**When to use:** At both cached return sites — the `gem` ORM object is already fetched, no extra DB call.

```python
# Source: [VERIFIED: views.py lines 1047-1061, 1110-1124 — existing pattern]
# Before:
'score_breakdown': {},

# After (both sites):
'score_breakdown': gem.score_breakdown,
# Also fix explanation on the race-condition branch (line 1120):
'explanation': gem.explanation,
```

Note: The first cached branch already reads `gem.explanation` correctly at line 1057. The race-condition branch at line 1120 reads `gem.explanation` correctly too. The only field incorrectly hardcoded is `score_breakdown: {}` at both sites.

### Pattern 3: _build_gem_explanation pure function (EXPLAIN-01)

**What:** Module-level private function in `views.py`, before `get_daily_gem`.
**When to use:** Called exactly once — inside `get_or_create` defaults on fresh branch.

```python
# Source: [VERIFIED: decisions D-01 through D-06 from CONTEXT.md + views.py inspection]
def _build_gem_explanation(breakdown: dict, track_name: str, artist_name: str, source: str) -> str:
    """
    Pure function: deterministic explanation sentence from dominant score component.
    No external calls. Zero latency risk.
    """
    if not breakdown:
        return "Picked based on your listening patterns"

    components = {
        'genre_sim': breakdown.get('genre_sim', 0.0),
        'novelty': breakdown.get('novelty', 0.0),
        'feedback_multiplier': breakdown.get('feedback_multiplier', 0.0),
    }
    if max(components.values()) == 0.0:
        return "Picked based on your listening patterns"

    dominant = max(components, key=components.get)
    source_str = f"via {source}" if source else "via discovery"

    if dominant == 'genre_sim':
        pct = round(components['genre_sim'] * 100)
        return f"Matches your listening taste — genre similarity: {pct}%, discovered {source_str}"
    elif dominant == 'novelty':
        return f"A hidden gem — low popularity score makes it a genuine discovery, found {source_str}"
    else:  # feedback_multiplier
        return f"You've liked {artist_name} before — that feedback boosted this pick, sourced {source_str}"
```

Notes on genre name: The `breakdown` dict produced by `_score_recommendations` does NOT include a genre name — it only has numeric scores. Genre name extraction would require a separate DB lookup. Per D-02 and the discretion note in CONTEXT.md, use `"your listening taste"` as the fallback label when no genre name is available. The `%` value comes from `breakdown['genre_sim']` which is already in scope.

### Pattern 4: was_saved non-fatal wiring (METRIC-01 / D-07 through D-09)

**What:** After the successful Spotify save call in `add_track_to_liked`, add a try/except block that updates the gem row.
**When to use:** Immediately after `sp.current_user_saved_tracks_add([track_id])` at line 843, before the `return JsonResponse({'message': 'all good'})`.

```python
# Source: [VERIFIED: views.py lines 631-637 — was_liked non-fatal pattern]
sp.current_user_saved_tracks_add([track_id])

# Non-fatal was_saved sync — mirrors was_liked pattern from submit_feedback
try:
    today = timezone.localdate()
    DailyGem.objects.filter(
        user=request.user,
        date=today,
        track__spotify_id=track_id,
    ).update(was_saved=True)
except Exception:
    pass  # Silent no-op — Spotify save already succeeded

return JsonResponse({'message': 'all good'})
```

Key distinction from the `was_liked` pattern: use `.update(was_saved=True)` (bulk update, no `save(update_fields=[...])`) because we look up by `track__spotify_id` via the FK relationship, not by gem PK. If the filter matches zero rows, `.update()` silently returns 0 — no error raised.

### Pattern 5: compound_hit_rate metric (METRIC-02 / D-12, D-13)

**What:** Add `compound_hit_rate` key to the `get_recommendation_metrics` response.
**When to use:** In the existing metrics view, immediately after `gem_acceptance_rate` is computed (line ~424).

```python
# Source: [VERIFIED: views.py lines 421-424 — gem_acceptance_rate pattern]
# Existing:
gem_acceptance_rate = gem_liked / gem_total

# Add after:
compound_hits = sum(
    1 for g in gem_list
    if g['was_liked'] is True or g['was_saved'] is True
)
compound_hit_rate = compound_hits / gem_total if gem_total > 0 else 0.0
```

Then add `'compound_hit_rate': compound_hit_rate` to the `return JsonResponse({...})` dict. The `gem_list` query on line 415 currently fetches `was_liked` but NOT `was_saved` — it must be updated to include `was_saved`:

```python
# Before (line 415):
gem_list = list(gems.values('was_liked', 'track_popularity', 'date', 'track_id'))

# After:
gem_list = list(gems.values('was_liked', 'was_saved', 'track_popularity', 'date', 'track_id'))
```

This is required or `g['was_saved']` will raise `KeyError`. [VERIFIED: views.py line 415]

### Anti-Patterns to Avoid

- **Adding an extra DB round-trip in cached branches:** The gem object is already in scope — read `gem.score_breakdown` directly. Do not call `DailyGem.objects.get()` again.
- **Raising in _build_gem_explanation:** Any exception inside the defaults dict of `get_or_create` aborts the gem creation. The function MUST be exception-safe — use empty dict fallback guard at the top.
- **Using `.save(update_fields=['was_saved'])` in add_track_to_liked:** `.update()` is the right call here because we have no gem PK — we look up by `track__spotify_id`. `.save()` requires a fetched instance.
- **Omitting was_saved from gem_list values() call:** Without adding `'was_saved'` to the `.values()` call, `g['was_saved']` in the compound_hit_rate loop will raise `KeyError` at runtime.
- **Conditional compound_hit_rate key:** The key must appear in the response JSON even when 0.0. Frontend Phase 8 expects it unconditionally (D-13).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dominant component selection | Custom sort / if-chain | `max(components, key=components.get)` | Standard Python dict-max idiom — one line, readable, exception-safe |
| Non-fatal DB update | Manual gem fetch + field set + save | `.update(was_saved=True)` on queryset | ORM bulk update returns 0 silently when no rows match — no exception path to handle |
| Source string from breakdown | New lookup / mapping | `breakdown.get('source', '')` | Already in score_breakdown dict from `_score_recommendations` line 879 |

---

## Common Pitfalls

### Pitfall 1: was_saved lookup fails silently because track__spotify_id != track_id param

**What goes wrong:** `DailyGem.objects.filter(user=..., date=today, track__spotify_id=track_id)` returns 0 rows even though the gem exists, because the DailyGem's Track FK uses `track.spotify_id` (the Spotify string ID) and the `track_id` param from the request is also the Spotify string ID — these match. But if the Track row was never created for this spotify_id, the FK lookup finds nothing.

**Why it happens:** The daily gem Track is created via `Track.objects.get_or_create(spotify_id=...)` in the fresh branch. If the user saved a track that was never their daily gem, no Track row exists. Per D-08 this is a silent no-op — correct behavior.

**How to avoid:** No fix needed. The `.update()` returning 0 is the intended silent no-op. The `try/except` wrapper handles any unexpected DB errors.

**Warning signs:** If tests assert `was_saved=True` after a save of a non-gem track and the test passes, the test setup is wrong (the Track row must exist for the FK lookup to work).

### Pitfall 2: score_breakdown missing from gem_list .values() call breaks compound_hit_rate

**What goes wrong:** `get_recommendation_metrics` builds `gem_list` with `.values('was_liked', 'track_popularity', 'date', 'track_id')`. If `was_saved` is not added to this list before computing `compound_hit_rate`, iterating `gem_list` and accessing `g['was_saved']` raises `KeyError` in production.

**Why it happens:** Django's `.values()` only returns explicitly requested fields. This is an easy omission when adding a new metric.

**How to avoid:** Add `'was_saved'` to the `.values()` call at line 415 in the same edit as adding the compound_hit_rate computation.

**Warning signs:** `KeyError: 'was_saved'` in server logs on the first metrics request after deployment.

### Pitfall 3: get_or_create race-condition branch skips explanation on new field

**What goes wrong:** The race-condition branch at line 1106 returns `gem.explanation` — which is correct for the field that existed before Phase 7. But if `explanation` was `''` because the gem was created before Phase 7's `_build_gem_explanation` wiring, this is intentional (no backfill). The only fix is for fresh gems going forward.

**Why it happens:** Gems created before Phase 7 have `explanation=''` — this is expected. The cached branch now reads from DB, so pre-Phase-7 gems return `''` explanation (not a bug).

**How to avoid:** No code fix needed. Document in test assertions that pre-existing gems return `explanation=''`.

### Pitfall 4: _build_gem_explanation called with `source` not extracted from breakdown

**What goes wrong:** `breakdown.get('source', '')` is the correct extraction — confirmed at `_score_recommendations` line 879 which stores `'source': rec.get('source', '')` inside the breakdown dict. If the caller passes `gem_data.get('source', '')` (top-level key, not from breakdown), this also works — `gem_data` has a top-level `source` key too.

**Why it happens:** The source string exists at two levels: top-level `gem_data['source']` and inside `gem_data['score_breakdown']['source']`. Either works; they carry the same value.

**How to avoid:** Use `breakdown.get('source', '')` for consistency — the helper already receives `breakdown` as its first arg.

---

## Code Examples

### Verified existing patterns that Phase 7 must match

#### was_liked non-fatal pattern (template for was_saved)
```python
# Source: [VERIFIED: views.py lines 631-637]
gem = DailyGem.objects.filter(
    user=request.user, date=timezone.localdate(), track=track
).first()
if gem:
    gem.was_liked = None
    gem.save(update_fields=['was_liked'])
```

Note: was_saved uses `.update()` instead of `.save(update_fields=[...])` because the lookup is by `track__spotify_id` (no object instantiation), not by a fetched object.

#### gem_acceptance_rate pattern (direct analog for compound_hit_rate)
```python
# Source: [VERIFIED: views.py lines 421-424]
gem_liked = sum(1 for g in gem_list if g['was_liked'] is True)
gem_acceptance_rate = gem_liked / gem_total
```

#### get_or_create with defaults (current state — to be expanded)
```python
# Source: [VERIFIED: views.py lines 1095-1105]
gem, created = DailyGem.objects.get_or_create(
    user=request.user,
    date=today,
    defaults={
        'track': track_obj,
        'explanation': '',
        'image_url': gem_data.get('image_url') or '',
        'preview_url': gem_data.get('preview_url') or '',
        'track_popularity': gem_data.get('popularity', 0),
    },
)
```

#### score_breakdown structure (from engine — what the view receives)
```python
# Source: [VERIFIED: hybrid_recommendation_engine.py lines 875-880]
rec['score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'source': rec.get('source', ''),
}
rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier
```

`gem_data['score']` is the `score_total` value. `gem_data['score_breakdown']` is the breakdown dict. Both are available at line 1082 after `gem_data = candidates[0]`.

---

## Runtime State Inventory

> Not applicable — this is a fresh wiring phase. No renames or data migrations.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | DailyGem rows with `score_breakdown={}`, `score_total=null`, `explanation=''` (pre-Phase 7) | None — pre-existing rows stay as-is; wiring is forward-only per CONTEXT.md deferred section |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 7 is code-only changes in views.py with no new external dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + Django TestCase |
| Config file | `backend/tests/conftest.py` (sets `DJANGO_SETTINGS_MODULE=config.settings`) |
| Quick run command | `cd backend && python3 -m pytest tests/test_feedback.py tests/test_metrics.py tests/test_views_gem_feedback.py -q` |
| Full suite command | `cd backend && python3 -m pytest tests/ -q` |

**Current baseline:** 46 tests pass across the 3 affected test files. [VERIFIED: ran 2026-05-14]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHEMA-02 | `score_breakdown` and `score_total` written to DailyGem on fresh branch | unit (ORM + view mock) | `pytest tests/test_views_gem_feedback.py -k "fresh" -x` | Wave 0 gap |
| SCHEMA-03 | `taste_vector_snapshot` captured at creation time | unit (ORM + view mock) | `pytest tests/test_views_gem_feedback.py -k "snapshot" -x` | Wave 0 gap |
| SCHEMA-04 | Cached branches return `gem.score_breakdown` (not `{}`) | unit (view-level) | `pytest tests/test_views_gem_feedback.py::TestGetDailyGemCached -x` | Extend existing |
| EXPLAIN-01 | `_build_gem_explanation` produces correct sentences for each dominant component | unit (pure function) | `pytest tests/test_views_gem_feedback.py -k "explanation" -x` | Wave 0 gap |
| EXPLAIN-02 | `DailyGem.explanation` non-empty after fresh gem creation | unit (ORM round-trip) | `pytest tests/test_views_gem_feedback.py -k "explanation" -x` | Wave 0 gap |
| METRIC-02 | `compound_hit_rate` key present in metrics response | unit (endpoint) | `pytest tests/test_metrics.py -k "compound" -x` | Wave 0 gap |

### Sampling Rate

- **Per task commit:** `cd backend && python3 -m pytest tests/test_feedback.py tests/test_metrics.py tests/test_views_gem_feedback.py -q`
- **Per wave merge:** `cd backend && python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test class `TestBuildGemExplanation` in `tests/test_views_gem_feedback.py` — covers EXPLAIN-01 (pure function, 4 cases: genre dominant, novelty dominant, feedback dominant, empty breakdown)
- [ ] New test class `TestGetDailyGemFreshScores` in `tests/test_views_gem_feedback.py` — covers SCHEMA-02, SCHEMA-03, EXPLAIN-02 (mocked engine, verify DB row has score_breakdown, score_total, taste_vector_snapshot, explanation after fresh creation)
- [ ] Extend `TestGetDailyGemCached.test_returns_cached_gem_without_engine_call` in `tests/test_views_gem_feedback.py` — assert `score_breakdown` == gem's persisted value, not `{}` (SCHEMA-04)
- [ ] New test class `TestWasSavedWiring` in `tests/test_feedback.py` — covers METRIC-01 wiring: mock Spotify client, verify `DailyGem.was_saved=True` after save; non-matching track_id is silent no-op
- [ ] Extend `TestMetricsEndpoint` in `tests/test_metrics.py` — add `test_compound_hit_rate_in_response` and `test_compound_hit_rate_formula` (METRIC-02)

---

## Security Domain

No new security surfaces introduced. Phase 7 makes no changes to authentication, input validation, or data access patterns. All modified views are already guarded with `@permission_classes([IsAuthenticated])`. The `track_id` param used in the `was_saved` lookup is an existing input already passed to `sp.current_user_saved_tracks_add([track_id])` — no new attack surface.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `gem_data['score']` is the `score_total` value (engine stores it as `rec['score']`) | Code Examples, Pattern 1 | Wrong field name would store null instead of the float score — low risk; VERIFIED by `_score_recommendations` line 883 |

**All other claims in this research are VERIFIED from direct codebase inspection (2026-05-14).**

---

## Open Questions

None — all implementation questions were resolved in the Phase 7 context session. The codebase inspection confirms all referenced line numbers and patterns exist as expected.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: backend/apps/core/views.py]` — `get_daily_gem` (lines 1026-1144), `add_track_to_liked` (lines 831-854), `get_recommendation_metrics` (lines 404-496), `submit_feedback` was_liked pattern (lines 631-694)
- `[VERIFIED: backend/apps/core/models.py]` — `DailyGem` field definitions including all Phase 6 fields (lines 280-302)
- `[VERIFIED: backend/apps/recommendations/hybrid_recommendation_engine.py]` — `_score_recommendations` return structure (lines 831-890)
- `[VERIFIED: backend/tests/test_feedback.py]` — `TestDailyGemWasLikedSync` and `TestDailyGemNewFields` test patterns
- `[VERIFIED: backend/tests/test_views_gem_feedback.py]` — view-level test patterns with mock engine
- `[VERIFIED: backend/tests/test_metrics.py]` — metrics endpoint test patterns
- `[VERIFIED: test run 2026-05-14]` — 46 tests pass in affected files

### Secondary (MEDIUM confidence)
- `.planning/phases/07-backend-wiring/07-CONTEXT.md` — locked decisions and exact line number references

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns from direct codebase inspection
- Architecture: HIGH — all 4 edit sites verified by file read; line numbers confirmed
- Pitfalls: HIGH — derived from actual code structure (e.g., `.values()` fields, FK lookup path)

**Research date:** 2026-05-14
**Valid until:** Stable (no external dependencies; valid until views.py is restructured)

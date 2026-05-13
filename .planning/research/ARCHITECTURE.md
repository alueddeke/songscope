# Architecture Patterns: Explainability + Compound Hit Tracking

**Domain:** Score breakdown persistence and explanation API for a Django REST + Next.js recommendation app
**Researched:** 2026-05-13
**Overall confidence:** HIGH — all findings grounded in direct code inspection of the existing codebase

---

## Existing System Snapshot (what is already wired)

### Models in scope

| Model | Relevant fields | Gap |
|-------|----------------|-----|
| `DailyGem` | `track`, `date`, `explanation` (TextField blank), `was_liked`, `was_skipped`, `track_popularity`, `image_url`, `preview_url` | No score component columns; no compound-hit column |
| `RecommendationLog` | `track`, `liked`, `source`, `track_popularity`, `was_novel` | No score component columns |
| `UserFeedback` | `feedback_type` (LIKE/DISLIKE/SAVE/SKIP/PLAY) | SAVE and PLAY choices defined but never written by any view |
| `UserProfile` | `data` JSONField holding `taste_vector`, `source_stats`, `preferences`, `cache` | Nothing persists score breakdown yet |

### Engine output (what `_score_recommendations` already returns)

`_score_recommendations()` in `hybrid_recommendation_engine.py` already writes a `score_breakdown` dict onto every candidate dict in memory:

```python
rec['score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'source': rec.get('source', ''),
}
```

This value is referenced in `get_daily_gem` (views.py line 1139):

```python
'score_breakdown': gem_data.get('score_breakdown', {}),
```

It is returned on the **fresh branch only**. On the **cached branch** it is always `{}`. It is **never persisted** to the DB.

### Existing `add_track_to_liked` view

`POST /api/add-track-to-liked/` calls `sp.current_user_saved_tracks_add([track_id])` and returns `{"message": "all good"}`. It does **not** write any DB record recording the save event.

### Frontend `DailyGem.tsx` interface

The `DailyGemResponse` TypeScript interface already has `explanation: string` but no `score_breakdown` field. The `explanation` field renders inside a `<blockquote>` when non-empty. `AddToLiked` is rendered inside `DailyGem` — it is the compound-hit trigger point.

---

## Question 1: Persisting score component values

### Recommendation: Add three Float columns to `DailyGem`

**What to add:**

```python
# DailyGem model additions
score_genre_sim      = models.FloatField(null=True, blank=True)
score_novelty        = models.FloatField(null=True, blank=True)
score_feedback_mult  = models.FloatField(null=True, blank=True)
score_total          = models.FloatField(null=True, blank=True)
```

**Why columns, not a JSON field:**

The score formula is `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`. These three components are a **fixed, named schema** — not an open-ended attribute bag. Flat Float columns allow direct ORM aggregation (`DailyGem.objects.filter(user=u).aggregate(Avg('score_genre_sim'))`), index use, and are self-documenting in the schema. A JSONField would add indirection for no gain at this cardinality.

**Why `DailyGem` and not `RecommendationLog`:**

`DailyGem` is the one-per-day authoritative recommendation record already joined to the feedback outcome (`was_liked`). Persisting scores there makes the `(score_components, outcome)` training pair available in a single table — essential for the future evaluation dashboard and hit-prediction retraining (both listed as future milestones in PROJECT.md). `RecommendationLog` holds the full candidate history; adding scores there too would mean 10x the rows scored vs. the one gem actually shown.

**Where to write the values:**

In `get_daily_gem` (views.py), the `DailyGem.objects.get_or_create` call already populates `track_popularity`. Extend `defaults` with the four score fields sourced from `gem_data['score_breakdown']`:

```python
# views.py get_daily_gem — fresh branch, DailyGem.objects.get_or_create
breakdown = gem_data.get('score_breakdown', {})
gem, created = DailyGem.objects.get_or_create(
    user=request.user,
    date=today,
    defaults={
        'track': track_obj,
        'explanation': '',
        'image_url': gem_data.get('image_url') or '',
        'preview_url': gem_data.get('preview_url') or '',
        'track_popularity': gem_data.get('popularity', 0),
        'score_genre_sim':     breakdown.get('genre_sim'),
        'score_novelty':       breakdown.get('novelty'),
        'score_feedback_mult': breakdown.get('feedback_multiplier'),
        'score_total':         gem_data.get('score'),
    },
)
```

**Migration risk:** Zero schema change to existing populated columns. The four new columns are all `null=True` so the migration is an `ALTER TABLE ... ADD COLUMN` with no backfill requirement. Single-user SQLite — migration is safe without a maintenance window.

---

## Question 2: Adding `explanation` object to `get_daily_gem` without breaking the existing contract

### Current response contract (both branches)

```json
{
  "track": { "id", "name", "artist", "album", "popularity", "image_url", "preview_url" },
  "explanation": "",
  "date": "2026-05-13",
  "cached": true,
  "score_breakdown": {}
}
```

`DailyGem.tsx` already destructures `{ track, explanation, date }` and ignores `score_breakdown`. Frontend is additive-safe — unknown keys are ignored.

### Recommendation: Enrich `score_breakdown` to be a structured explanation object; keep `explanation` as the text field

The cleanest non-breaking extension is to **populate `score_breakdown` on both branches** (currently `{}` on cached) and add a structured `explanation_data` key alongside the existing `explanation` text key:

```json
{
  "track": { ... },
  "explanation": "Matches your taste in indie folk (78%), low-profile gem, liked artist bonus",
  "explanation_data": {
    "genre_sim_pct":       78,
    "novelty_pct":         91,
    "feedback_mult_label": "liked artist",
    "source_label":        "playlist mining"
  },
  "score_breakdown": {
    "genre_sim":          0.78,
    "novelty":            0.91,
    "feedback_multiplier": 1.5,
    "source":             "playlist_mining"
  },
  "date": "2026-05-13",
  "cached": true
}
```

`explanation` remains a plain string — the existing `<blockquote>` render in `DailyGem.tsx` needs no change. `explanation_data` is a new key the frontend can use to render a score breakdown UI without parsing the text string. `score_breakdown` is populated from the persisted DB values on the cached branch so the fields are consistent across both branches.

**Cached branch fix:** Read `score_breakdown` from `DailyGem` row fields, not from a re-run of the engine:

```python
# Cached branch response
return JsonResponse({
    'track': { ... },
    'explanation': gem.explanation,
    'explanation_data': _build_explanation_data(gem),
    'score_breakdown': {
        'genre_sim':          gem.score_genre_sim,
        'novelty':            gem.score_novelty,
        'feedback_multiplier': gem.score_feedback_mult,
        'source':             gem.track.name,  # source is on RecommendationLog, not DailyGem
    },
    'date': str(gem.date),
    'cached': True,
})
```

---

## Question 3: Server-side vs client-side natural language explanation

### Recommendation: Server-side generation, stored in `DailyGem.explanation`, triggered at creation time

**Rationale:**

1. The `explanation` TextField already exists on `DailyGem`. The field is already returned to the frontend and rendered. The only missing piece is writing a non-empty value.
2. Generating it server-side at recommendation time (not on every request) means zero latency on cache hits. The text is computed once and stored.
3. Client-side generation from score numbers (`genre_sim=0.78 → "78% genre match"`) is cheap but produces mechanical copy ("Genre: 78%, Novelty: 91%"). A short deterministic template string server-side is richer and interview-demonstrable.
4. The project already uses OpenAI for `submit_ai_feedback`. The `$1/day` budget constraint means GPT should be avoided for explanation generation (it fires on every new gem, every user). Use a **deterministic template** instead.

**Deterministic template approach (no LLM cost):**

```python
def _build_gem_explanation(breakdown: dict, track_name: str, artist_name: str) -> str:
    """
    Build a natural-language explanation string from score components.
    No LLM call — deterministic templates keep cost at zero.
    """
    parts = []
    genre_pct = round(breakdown.get('genre_sim', 0) * 100)
    novelty   = breakdown.get('novelty', 0)
    fb_mult   = breakdown.get('feedback_multiplier', 1.0)

    if genre_pct >= 60:
        parts.append(f"strong genre match ({genre_pct}% overlap with your taste)")
    elif genre_pct >= 30:
        parts.append(f"partial genre match ({genre_pct}%)")
    else:
        parts.append("genre-diverse pick — outside your usual territory")

    if novelty >= 0.7:
        parts.append("low-profile gem most listeners haven't found yet")
    elif novelty >= 0.4:
        parts.append("moderately under the radar")

    if fb_mult > 1.2:
        parts.append(f"bonus: you've liked {artist_name}'s work before")
    elif fb_mult < 0.8:
        parts.append(f"note: you've skipped {artist_name} before — trying a different cut")

    source = breakdown.get('source', '')
    source_label = {
        'playlist_mining':  'surfaced from your playlists',
        'artist_network':   'from an artist you follow',
        'related_artists':  'from an artist similar to ones you love',
        'contextual':       'matched to your listening time patterns',
    }.get(source, '')
    if source_label:
        parts.append(source_label)

    return "; ".join(parts).capitalize() + "." if parts else ""
```

**Where to call it:** In `get_daily_gem`, fresh branch, immediately before or inside the `get_or_create` defaults. Write the result into `DailyGem.explanation`.

**`_build_explanation_data` helper (for structured UI):**

```python
def _build_explanation_data(gem: DailyGem) -> dict:
    return {
        'genre_sim_pct':       round((gem.score_genre_sim or 0) * 100),
        'novelty_pct':         round((gem.score_novelty or 0) * 100),
        'feedback_mult_label': (
            'liked artist'   if (gem.score_feedback_mult or 1.0) > 1.2 else
            'skipped artist' if (gem.score_feedback_mult or 1.0) < 0.8 else
            'neutral'
        ),
    }
```

This lives in `views.py` (private helper) or a new `apps/core/explanation.py` module if it grows.

---

## Question 4: Tracking compound success (played + saved/liked)

### Definition

Binary hit = user **added to Spotify liked songs** via the `Add to Liked` button. This is the clearest proxy for "genuine discovery" given the constraints (no Spotify playback event webhooks, no Premium-only play counts).

Playing the 30s preview is observable client-side but audio preview plays are a weak signal — the user may be auditing rather than discovering. The stronger signal is the explicit Spotify save.

### Recommendation: Add `was_saved_to_spotify` BooleanField to `DailyGem`

```python
# DailyGem model addition
was_saved_to_spotify = models.BooleanField(null=True, blank=True)
```

**Compound hit derived field:**

A hit is `was_liked = True AND was_saved_to_spotify = True`. This is a read-time computation, not a stored column — compute it in the metrics view as needed. No additional column needed.

**Preview-play tracking (optional, low priority):**

If preview play tracking is desired, add `was_previewed = models.BooleanField(default=False)` to `DailyGem`. This can be set via a lightweight endpoint or piggybacked on the cached-branch `DailyGem` fetch. It is optional for the v1.1 milestone; the Spotify save is sufficient as the primary hit signal.

---

## Question 5: Where to update the compound hit signal

### Recommendation: Extend `add_track_to_liked` view — do NOT put it in `submit_feedback`

**Why not `submit_feedback`:**

`submit_feedback` handles thumbs-up/thumbs-down. Adding Spotify-save logic there conflates two distinct user actions that are independently meaningful for learning:
- A LIKE without saving = "I enjoyed the recommendation in context"
- A save without a LIKE = "I liked it enough to save it without leaving explicit feedback"
- Both together = compound hit

Keeping them separate preserves signal fidelity for future ML work.

**What `add_track_to_liked` should do (extended):**

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_track_to_liked(request):
    track_id = request.data.get("track_id")
    if not track_id:
        return JsonResponse({'error': 'track_id is required'}, status=400)

    # ... existing Spotify save logic ...
    sp.current_user_saved_tracks_add([track_id])

    # NEW: record compound-hit signal on DailyGem if this track is today's gem
    try:
        track_obj = Track.objects.filter(spotify_id=track_id).first()
        if track_obj:
            DailyGem.objects.filter(
                user=request.user,
                track=track_obj,
            ).update(was_saved_to_spotify=True)
    except Exception as save_err:
        logger.warning(f"Failed to record was_saved_to_spotify: {save_err}")
        # Non-fatal — Spotify save succeeded; don't 500 over a DB annotation

    return JsonResponse({'message': 'all good'})
```

No new endpoint needed. The existing frontend `AddToLiked` component calls `POST /api/add-track-to-liked/` — this is already wired in both `DailyGem.tsx` and `Recommendation.tsx`. The DB update is a silent annotation; the response contract does not change.

Note: The `filter(...).update()` pattern (not `get`) is intentional — if the same track was shown on multiple past dates, all matching gems get annotated. This is correct: saving the track is a retroactive signal that the recommendation was good regardless of when it was shown.

---

## Component Map: New vs Modified

### New

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `_build_gem_explanation()` | Python helper function | `apps/core/views.py` or `apps/core/explanation.py` | Deterministic text explanation from score breakdown |
| `_build_explanation_data()` | Python helper function | same | Structured dict for frontend score breakdown UI |
| Migration `0008_dailygem_scores_hit.py` | Django migration | `apps/core/migrations/` | Adds `score_genre_sim`, `score_novelty`, `score_feedback_mult`, `score_total`, `was_saved_to_spotify` to `DailyGem` |
| `ScoreBreakdown` (frontend) | React component | `frontend/app/profile/components/DailyGem/` | Renders genre%, novelty%, source label from `explanation_data` |

### Modified

| Component | Change | Risk |
|-----------|--------|------|
| `DailyGem` model | +5 nullable columns | Low — all nullable, additive |
| `get_daily_gem` view | Persist scores + explanation on fresh branch; populate `score_breakdown` + `explanation_data` on cached branch | Low — cached branch currently returns `{}` for `score_breakdown`; this is an enrichment |
| `add_track_to_liked` view | Add `DailyGem.was_saved_to_spotify` update after Spotify API call | Low — failure is caught and logged; response unchanged |
| `DailyGem.tsx` | Add `explanation_data` to interface; render `ScoreBreakdown` component | Low — additive; existing fields unchanged |

### Unchanged

| Component | Reason |
|-----------|--------|
| `_score_recommendations()` in `HybridRecommendationEngine` | Already writes `score_breakdown` to candidate dict — no change needed |
| `submit_feedback` view | Compound hit handled in `add_track_to_liked`, not here |
| `RecommendationLog` model | Score persistence only on `DailyGem` (the one-per-day authoritative record) |
| `FeedbackButtonGroup` | LIKE/DISLIKE thumbs are separate from the Spotify save action |

---

## Data Flow

```
HybridRecommendationEngine._score_recommendations()
  └─ writes rec['score_breakdown'] = { genre_sim, novelty, feedback_multiplier, source }
       │
       ▼
get_daily_gem (fresh branch)
  ├─ calls _build_gem_explanation(breakdown, track_name, artist_name)
  ├─ persists DailyGem { score_genre_sim, score_novelty, score_feedback_mult, score_total, explanation }
  └─ returns { track, explanation, explanation_data, score_breakdown, date, cached: false }

get_daily_gem (cached branch)
  ├─ reads DailyGem.score_* columns
  ├─ calls _build_explanation_data(gem)
  └─ returns { track, explanation, explanation_data, score_breakdown, date, cached: true }

add_track_to_liked (POST)
  ├─ calls sp.current_user_saved_tracks_add([track_id])       ← existing
  └─ DailyGem.objects.filter(user, track).update(was_saved_to_spotify=True)  ← new

Compound hit query (metrics view, evaluation dashboard):
  DailyGem.objects.filter(user=u, was_liked=True, was_saved_to_spotify=True)
```

---

## Build Order

Dependencies flow strictly DB → API → Frontend. Migration must land before the view reads/writes the new columns.

### Phase 1: DB schema (no API or frontend changes)

1. Add `score_genre_sim`, `score_novelty`, `score_feedback_mult`, `score_total`, `was_saved_to_spotify` to `DailyGem` model (all `null=True, blank=True`)
2. Generate and apply migration `0008_...`
3. Verify: `python manage.py showmigrations core` shows the migration applied

**Dependencies:** None. Safe to deploy independently.

### Phase 2: Backend — persist scores and explanation at recommendation time

1. Implement `_build_gem_explanation(breakdown, track_name, artist_name)` helper
2. Implement `_build_explanation_data(gem)` helper
3. Extend `get_daily_gem` fresh-branch `get_or_create` to write score columns + explanation
4. Extend `get_daily_gem` cached-branch response to include `explanation_data` + populated `score_breakdown` from DB columns
5. Extend `add_track_to_liked` to update `DailyGem.was_saved_to_spotify`
6. Update serializer/type annotations as needed (no DRF serializer exists for `get_daily_gem`; it returns raw `JsonResponse`)

**Dependencies:** Phase 1 migration must be applied.

### Phase 3: Frontend — render score breakdown

1. Add `explanation_data` and `score_breakdown` to `DailyGemResponse` TypeScript interface in `DailyGem.tsx`
2. Build `ScoreBreakdown` component that renders three bars/badges: Genre Match %, Novelty %, and Feedback Signal label
3. Render `ScoreBreakdown` below the existing `<blockquote>` explanation block (or replace it with a richer layout)
4. `AddToLiked` component requires no changes — the backend now silently records the save

**Dependencies:** Phase 2 API changes must be deployed (or mocked for local dev).

### Phase 4: Metrics integration (can be deferred)

1. Add `was_saved_to_spotify` and compound hit rate to `get_recommendation_metrics` view
2. Extend `MetricsStrip` component to show "Hit rate" (played + saved)

---

## Pitfalls Specific to This Milestone

### Pitfall 1: Cached branch `score_breakdown: {}` silently hides scores

The view already exists and the cached branch is the common path after day 1. If Phase 2 only populates scores on the fresh branch and forgets to backfill from DB columns on the cached branch, the UI will always show empty explanations for returning users. **Fix: always read from DB columns on cached branch as described above.**

### Pitfall 2: `score_breakdown` key missing from very old `DailyGem` rows

Rows created before the migration have `score_genre_sim = NULL`. `_build_explanation_data` must handle `None` gracefully (the helpers above use `or 0` defaults). The frontend must render a graceful empty state when all score values are null. **Fix: null-guard on both server and client.**

### Pitfall 3: `was_saved_to_spotify` update must not 500 the save action

The Spotify API call (`sp.current_user_saved_tracks_add`) is the user-visible action. The DB annotation is internal. If the DB update fails, the endpoint must still return 200. **Fix: wrap in try/except with logger.warning as shown above.**

### Pitfall 4: `explanation` TextField is blank-default — cached branch returns stale empty string

Old gems (before Phase 2) have `explanation = ""`. The frontend already guards against this (`{explanation && <blockquote>...}`) — no change needed on the frontend for old rows.

### Pitfall 5: `feedback_multiplier` is artist-level, not track-level

The explanation text references the artist name. If the user's `preferences.liked_artists` list changes after the recommendation, the stored explanation will not reflect the current state. This is intentional and correct — the explanation describes **why the gem was chosen at that moment**, not the current preference state. Document this as design intent in CONCEPTS.md.

---

## CONCEPTS.md + SYSTEM_DESIGN.md Update Requirements

Per project memory: CONCEPTS.md and SYSTEM_DESIGN.md must stay in sync with code changes.

**CONCEPTS.md additions needed:**

- `DailyGem.score_*` columns: what each component means, the locked formula, why these three components
- `was_saved_to_spotify` as the compound hit proxy: definition of binary hit, why save > play for signal quality
- Deterministic explanation generation: why templates over LLM (cost, latency, determinism)
- Compound hit rate as a training label for future supervised learning on `(score_components, hit)` pairs

**SYSTEM_DESIGN.md additions needed:**

- Updated `DailyGem` schema diagram showing new columns
- Updated `get_daily_gem` data flow diagram showing explanation generation step
- Updated `add_track_to_liked` description noting the compound-hit annotation side-effect
- New section: "Score Breakdown API" — endpoint contract, cached vs fresh branch differences

---

## Sources

All findings are derived from direct inspection of the following files at commit state 2026-05-13:

- `/Users/antonilueddeke/Desktop/Projects/songscope/backend/apps/core/models.py` — DailyGem, RecommendationLog, UserFeedback, Track model definitions
- `/Users/antonilueddeke/Desktop/Projects/songscope/backend/apps/core/views.py` — `get_daily_gem`, `add_track_to_liked`, `submit_feedback` view implementations
- `/Users/antonilueddeke/Desktop/Projects/songscope/backend/apps/recommendations/hybrid_recommendation_engine.py` — `_score_recommendations`, `_build_taste_vector`, `get_recommendation_weights`
- `/Users/antonilueddeke/Desktop/Projects/songscope/frontend/app/profile/components/DailyGem/DailyGem.tsx` — `DailyGemResponse` interface, render logic, `AddToLiked` usage
- `/Users/antonilueddeke/Desktop/Projects/songscope/frontend/app/profile/components/AddToLiked/AddToLiked.tsx` — existing add-to-liked flow
- `/Users/antonilueddeke/Desktop/Projects/songscope/.planning/PROJECT.md` — milestone context, constraints, future milestones
- Migration history `0001` through `0007` — confirms SQLite, existing column history

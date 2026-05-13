# Phase 3: Feedback Learning Loop - Research

**Researched:** 2026-05-11
**Domain:** Online learning, Thompson Sampling bandit, personalization engine wiring
**Confidence:** HIGH — all findings verified by direct codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Taste Vector Online Update**
- D-01: Update is immediate and online — on like/dislike, update `UserProfile.data['taste_vector'][genre]` in place and save to DB. Hook lives in `PersonalizationEngine.apply_feedback_learning()` (currently a no-op).
- D-02: Learning rate `lr = 0.1` (conservative, stable SGD). Same lr for both like and dislike directions.
- D-03: Like → `taste_vector[genre] += 0.1` for each genre on the liked track's artist(s). Dislike → `taste_vector[genre] -= 0.1`. No floor — vector entries can go negative (active genre avoidance).
- D-04: Unlike (toggle off a previous like) → reverse the update: `taste_vector[genre] -= 0.1` for genres that were incremented. Use `feedback_history` entries to retrieve the track's genres at undo time.
- D-05: Genres to update come from `Track.genres` field on the ORM object (populated via `sp.artist()` call when track is first created in `submit_feedback`).

**Thompson Sampling Bandit**
- D-06: Success = any positive feedback (LIKE or SAVE) on any recommended track. Source gets credit whenever its track earns positive feedback.
- D-07: Bandit state stored as `UserProfile.data['source_stats']`. Schema: `{'playlist_mining': {'s': 0, 'f': 0}, 'artist_network': {'s': 0, 'f': 0}, 'genre_search': {'s': 0, 'f': 0}, 'related_artists': {'s': 0, 'f': 0}, 'contextual': {'s': 0, 'f': 0}}`.
- D-08: Integration point: replace output of `get_recommendation_weights()`. At recommendation time, sample `Beta(s+1, f+1)` for each source and use sampled values as weights.
- D-09: All 5 sources continue to run every cycle.

**Popularity Targeting (Personalized Novelty)**
- D-10: Replace `novelty = 1 - (popularity / 100)` with a bell-curve novelty centered on `preferred_popularity_range['midpoint']`.
- D-11: Cold start: `preferred_popularity_range` initialized to `{'midpoint': 30, 'width': 20}`.
- D-12: Like → `midpoint += 0.1 * (track_popularity - midpoint)`. Dislike → `midpoint -= 0.1 * (track_popularity - midpoint)`.

**"Why This Gem" Explanation**
- D-13: Pass score breakdown into `RecommendationExplainer` prompt context. One prompt change to `ai_feedback_service.py`.
- D-14: Return score breakdown in `/api/daily-gem/` response: `{"explanation": "...", "score_breakdown": {"genre_sim": float, "novelty": float, "feedback_multiplier": float, "top_genres": [...]}}`.

### Claude's Discretion
- Exact bell-curve formula (Gaussian vs triangular) — planner chooses based on simplicity.
- `width` parameter behavior — whether fixed or also updates over time.
- Cold-start threshold for bandit (suggest N=3 per source before trusting bandit).

### Deferred Ideas (OUT OF SCOPE)
- Collaborative filtering across users
- Audio feature weights revival
- Source skipping via bandit
</user_constraints>

---

## Summary

Phase 3 wires three ML mechanisms that build on Phase 2's infrastructure: (1) online taste vector updates, (2) Thompson Sampling bandit for source weighting, and (3) personalized novelty via a bell-curve popularity target. A new `/api/daily-gem/` Django view is also required — it does not currently exist in `urls.py`.

The core implementation is split across two engines. `PersonalizationEngine.apply_feedback_learning()` and `remove_feedback_learning()` are confirmed no-ops and will receive the online update logic. These methods hold only `self.user` and `self.preferences` (a `UserPreferences` object) — they must explicitly fetch `UserProfile` to mutate `UserProfile.data`. The bandit lives in `HybridRecommendationEngine.get_recommendation_weights()`, which currently returns a static dict and is called only by `get_profile_summary()` — NOT by `_score_recommendations()`. This means D-08's "zero changes to scoring code" claim requires clarification: the bandit weights must be incorporated into scoring via a new mechanism, not a drop-in replacement.

`track_info` dict passed to `add_feedback()` from `submit_feedback` has only `artist`, `name`, `album` — no `genres` key. Genre data for the online update must come from `feedback.track.genres` (the `Track` ORM field), accessed on the `UserFeedback` object that `apply_feedback_learning()` already receives.

**Primary recommendation:** Implement `apply_feedback_learning()` as the single point for taste vector + popularity range + bandit state updates; add a `_compute_source_weight()` helper to `HybridRecommendationEngine` that `_score_recommendations()` calls per-track to incorporate bandit weights into the score multiplier; create the `/api/daily-gem/` view with `DailyGem` persistence and `RecommendationExplainer`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Taste vector online update | API / Backend (`PersonalizationEngine`) | Database (`UserProfile.data` JSONField) | Mutates persisted user state; logic belongs server-side |
| Thompson Sampling bandit | API / Backend (`HybridRecommendationEngine`) | Database (`UserProfile.data['source_stats']`) | Sampling happens at recommendation time per-request |
| Popularity midpoint update | API / Backend (`PersonalizationEngine`) | Database (`UserProfile.data['preferences']`) | Same cadence and location as taste vector update |
| Unlike reversal | API / Backend (`PersonalizationEngine.remove_feedback_learning`) | Database (`UserProfile.data['preferences']['feedback_history']`) | Reads stored history to undo; same tier as apply |
| Score breakdown generation | API / Backend (`HybridRecommendationEngine._score_recommendations`) | — | Scoring happens there; breakdown is a side-product |
| "Why this gem" explanation | API / Backend (`RecommendationExplainer` in `ai_feedback_service.py`) | External (OpenAI GPT-4o-mini) | OpenAI prompt construction stays server-side |
| Daily gem persistence | API / Backend (`/api/daily-gem/` view) | Database (`DailyGem` model) | View creates/retrieves today's `DailyGem` record |
| Score breakdown display | Frontend (DailyGem component) | — | Frontend already renders `explanation`; `score_breakdown` can be added alongside |

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `numpy` | 2.1.3 | `numpy.random.beta(s+1, f+1)` for Thompson Sampling | VERIFIED: installed in venv |
| `math` | stdlib | `math.exp` for Gaussian bell curve | VERIFIED: stdlib, no install |
| `django.db.models` | Django (existing) | `UserProfile.objects.get()` in `apply_feedback_learning` | VERIFIED: existing imports |
| `openai` | NOT in venv | `RecommendationExplainer` GPT-4o-mini call | VERIFIED: missing from venv |

**Version verification:**
```bash
# numpy confirmed:
backend/venv/bin/python -c "import numpy; print(numpy.__version__)"
# Output: 2.1.3
# numpy.random.beta confirmed working:
backend/venv/bin/python -c "import numpy.random; print(numpy.random.beta(2,3))"
# Output: 0.177 (valid sample)
```

**Critical dependency gap:** `openai` is not installed in the project venv. The `ai_feedback_service.py` already handles the missing import gracefully (falls back to `_fallback_interpretation`), but `RecommendationExplainer.generate_explanation()` will need the same pattern. Wave 0 must include `pip install openai` in the venv if explanation quality matters.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `math.exp` | stdlib | Gaussian bell curve `exp(-((pop-mid)**2)/(2*width**2))` | Recommended over triangular (smoother, better interview story) |
| Django JSONField | existing | All new state stored in `UserProfile.data` | All bandit + popularity + taste vector state |

**Installation for openai:**
```bash
cd backend && venv/bin/pip install openai
```

---

## Architecture Patterns

### System Architecture Diagram

```
FEEDBACK EVENT (POST /api/submit-feedback/)
          │
          ▼
    submit_feedback view
          │
          ├─── PersonalizationEngine.apply_feedback_learning(UserFeedback)
          │         │
          │         ├─ fetch UserProfile (UserProfile.objects.get(user=self.user))
          │         ├─ update taste_vector[genre] += 0.1 * signal  (for each genre)
          │         ├─ update preferred_popularity_range midpoint
          │         └─ update source_stats[source]['s'|'f'] + save
          │
          └─── HybridRecommendationEngine.remove_feedback (only on unlike path)


RECOMMENDATION REQUEST (GET /api/daily-gem/)
          │
          ▼
    get_daily_gem view  ←── NEW: must be created
          │
          ├─ Check DailyGem for today → if exists, return cached
          │
          ├─ HybridRecommendationEngine.get_recommendations()
          │         │
          │         └─ _score_recommendations()
          │                   │
          │                   ├─ genre_sim (cosine similarity, unchanged)
          │                   ├─ novelty = bell_curve(popularity, midpoint, width)  ← CHANGES
          │                   ├─ feedback_multiplier (artist-level, unchanged)
          │                   ├─ source_weight = sample Beta(s+1, f+1)  ← NEW
          │                   └─ score = 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier
          │                             (source_weight applied as post-score multiplier OR
          │                              integrated into feedback_multiplier component)
          │
          ├─ Pick top-scored track not in exclusion set
          ├─ RecommendationExplainer.generate_explanation(track, score_breakdown)  ← NEW
          ├─ Create DailyGem record
          └─ Return {track, explanation, score_breakdown, date, cached: false}
```

### Recommended Project Structure (files to modify/create)
```
backend/
├── apps/
│   ├── recommendations/
│   │   ├── hybrid_recommendation_engine.py   # get_recommendation_weights() → bandit
│   │   │                                     # _score_recommendations() → bell-curve novelty
│   │   │                                     # _score_recommendations() → source weight
│   │   └── personalization_engine.py         # apply_feedback_learning() → activate
│   │                                         # remove_feedback_learning() → activate
│   ├── ai/
│   │   └── ai_feedback_service.py            # Add RecommendationExplainer class
│   └── core/
│       ├── views.py                          # Add get_daily_gem view
│       └── models.py                         # No changes needed
├── config/
│   └── urls.py                               # Add path('api/daily-gem/', ...)
└── tests/
    └── test_feedback_learning.py             # New: Phase 3 tests
```

### Pattern 1: Online Taste Vector Update in `apply_feedback_learning`

**What:** Mutate `UserProfile.data['taste_vector']` on every feedback event, then save.
**When to use:** On LIKE or DISLIKE, called from `submit_feedback` view.

```python
# Source: direct codebase inspection — models.py UserProfile.add_feedback() pattern
def apply_feedback_learning(self, feedback: UserFeedback):
    from apps.core.models import UserProfile
    lr = 0.1
    try:
        profile = UserProfile.objects.get(user=self.user)
    except UserProfile.DoesNotExist:
        logger.warning("apply_feedback_learning: no UserProfile for user %s", self.user.id)
        return

    data = profile.data
    taste_vector = data.setdefault('taste_vector', {})

    # genres come from Track.genres (populated via sp.artist() in submit_feedback)
    genres = list(feedback.track.genres or [])
    signal = 1.0 if feedback.feedback_type in ('LIKE', 'SAVE') else -1.0

    for genre in genres:
        taste_vector[genre] = taste_vector.get(genre, 0.0) + lr * signal

    # Popularity midpoint update (D-12)
    prefs = data.setdefault('preferences', {})
    pop_range = prefs.setdefault(
        'preferred_popularity_range', {'midpoint': 30, 'width': 20}
    )
    track_pop = feedback.track.popularity
    pop_range['midpoint'] += lr * (track_pop - pop_range['midpoint']) * signal

    # Bandit state update (D-07)
    source = _get_source_for_track(feedback.track, self.user)  # see Pattern 3
    source_stats = data.setdefault('source_stats', _default_source_stats())
    if source and source in source_stats:
        if feedback.feedback_type in ('LIKE', 'SAVE'):
            source_stats[source]['s'] += 1
        else:
            source_stats[source]['f'] += 1

    profile.data = data
    profile.save(update_fields=['data'])
```

### Pattern 2: Bell-Curve Novelty in `_score_recommendations`

**What:** Replace `1 - (popularity / 100)` with Gaussian centered on user's `preferred_popularity_range['midpoint']`.
**When to use:** Inside `_score_recommendations()`, novelty computation block only. Outer coefficients (0.4/0.3/0.3) are LOCKED.

```python
# Source: direct codebase inspection — existing _score_recommendations() + math stdlib
import math

def _bell_curve_novelty(self, popularity: int, midpoint: float, width: float) -> float:
    """Gaussian novelty peaked at midpoint. Returns 0.0–1.0."""
    return math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))

# Inside _score_recommendations(), replace:
#   novelty = 1.0 - (rec.get('popularity', 50) / 100.0)
# With:
pop_range = self.profile.data.get('preferences', {}).get(
    'preferred_popularity_range', {'midpoint': 30, 'width': 20}
)
novelty = self._bell_curve_novelty(
    rec.get('popularity', 50),
    pop_range['midpoint'],
    pop_range['width']
)
```

### Pattern 3: Thompson Sampling Bandit in `get_recommendation_weights`

**What:** Sample `Beta(s+1, f+1)` per source and return as weight dict.
**When to use:** Called from `_score_recommendations()` to get per-source weight; replaces the static dict.

```python
# Source: direct codebase inspection — UserProfile.get_recommendation_weights() +
#         numpy confirmed at 2.1.3 with numpy.random.beta verified
BANDIT_SOURCES = ['playlist_mining', 'artist_network', 'genre_search',
                  'related_artists', 'contextual']
COLD_START_N = 3  # planner decision per Claude's Discretion

def get_recommendation_weights(self):
    source_stats = self.profile.data.get('source_stats', {})
    weights = {}
    for source in BANDIT_SOURCES:
        stats = source_stats.get(source, {'s': 0, 'f': 0})
        total = stats['s'] + stats['f']
        if total < COLD_START_N:
            # Fall back to static weight until enough observations
            static = {'playlist_mining': 0.3, 'artist_network': 0.25,
                      'contextual': 0.2, 'genre_search': 0.15, 'related_artists': 0.1}
            weights[source] = static.get(source, 0.1)
        else:
            weights[source] = float(np.random.beta(stats['s'] + 1, stats['f'] + 1))
    return weights
```

**Integration into `_score_recommendations`:** The current `_score_recommendations` does NOT read source weights. The planner must choose one of:
- Option A: Multiply final score by `source_weights[rec['source']]` as a post-score multiplier (simplest, keeps locked formula intact: score = locked_formula * source_weight)
- Option B: Replace `feedback_multiplier` meaning to combine artist preference and source weight

Option A is recommended: `rec['score'] = (0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier) * source_weight`. This preserves the LOCKED formula for the additive components and adds the bandit as a multiplicative scaling factor. The CONTEXT.md says "zero changes to scoring code" but that presupposed the weights dict was already being consumed — it is not. Option A requires a minimal 1-line addition.

### Pattern 4: Unlike Reversal in `remove_feedback_learning`

**What:** Look up the track's historical genres from `feedback_history` (stored in `UserProfile.data`), reverse the taste vector update, reverse the popularity midpoint shift.
**When to use:** On toggle-unlike, called from `submit_feedback` view after `existing_feedback.delete()`.

```python
# Source: direct codebase inspection — UserProfile.data['preferences']['feedback_history']
# Each entry: {'track_id': str, 'feedback_type': str, 'timestamp': str, 'track_info': dict}
# Note: track_info in feedback_history has artist/name/album but NOT genres.
# Genres must come from Track.genres ORM lookup (track still exists after unlike).
def remove_feedback_learning(self, track_id: str):
    from apps.core.models import UserProfile, Track
    lr = 0.1
    try:
        profile = UserProfile.objects.get(user=self.user)
        track = Track.objects.filter(spotify_id=track_id).first()
    except UserProfile.DoesNotExist:
        return
    if not track:
        return

    # Find original feedback type from history
    history = profile.data.get('preferences', {}).get('feedback_history', [])
    original_entry = next(
        (e for e in reversed(history) if e.get('track_id') == track_id), None
    )
    if not original_entry:
        return

    original_type = original_entry.get('feedback_type', '')
    signal = 1.0 if original_type in ('LIKE', 'SAVE') else -1.0

    # Reverse taste vector update
    taste_vector = profile.data.setdefault('taste_vector', {})
    for genre in (track.genres or []):
        taste_vector[genre] = taste_vector.get(genre, 0.0) - lr * signal

    # Reverse popularity midpoint update
    prefs = profile.data.setdefault('preferences', {})
    pop_range = prefs.get('preferred_popularity_range', {'midpoint': 30, 'width': 20})
    pop_range['midpoint'] -= lr * (track.popularity - pop_range['midpoint']) * signal

    profile.save(update_fields=['data'])
```

### Pattern 5: Source Lookup for Bandit Credit

**What:** Determine which candidate source produced a track when feedback arrives.
**Problem:** `submit_feedback` does not receive the `source` from the frontend. The source is in `RecommendationLog`.

```python
# Source: direct codebase inspection — RecommendationLog.source field (Phase 2)
def _get_source_for_track(track, user):
    from apps.core.models import RecommendationLog
    log = RecommendationLog.objects.filter(
        user=user, track=track
    ).order_by('-recommended_at').first()
    return log.source if log else None
```

This pattern is already used in `submit_feedback` for `liked` field updates. It works correctly as long as `RecommendationLog.source` was populated at recommendation time (confirmed: `views.py` line 336 passes `source=track.get('source', '')`).

### Pattern 6: `RecommendationExplainer` Class (New)

**What:** Augment OpenAI prompt with score breakdown; return explanation string.
**Where:** Add to `ai_feedback_service.py` alongside `FeedbackInterpreter`.

```python
# Source: direct codebase inspection — FeedbackInterpreter pattern in ai_feedback_service.py
class RecommendationExplainer:
    def __init__(self):
        self.rate_limiter = RateLimitMonitor()
        self.openai_client = None
        self._initialize_openai()  # reuse same pattern as FeedbackInterpreter

    def generate_explanation(self, track_info: dict, score_breakdown: dict) -> str:
        """
        track_info: {name, artist, album, popularity}
        score_breakdown: {genre_sim: float, novelty: float,
                          feedback_multiplier: float, top_genres: list[str]}
        Returns: natural language explanation string
        """
        if not self.openai_client:
            return self._fallback_explanation(track_info, score_breakdown)
        # build prompt with score_breakdown values woven in
        # call gpt-4o-mini, return content string
```

### Pattern 7: New `/api/daily-gem/` View and URL Route

**What:** A new Django view that checks for an existing `DailyGem` for today; if absent, picks the top recommendation, generates an explanation, persists a `DailyGem` record, and returns the structured response.
**Why new:** The `/api/daily-gem/` endpoint is called by the frontend but does NOT exist in Django's `urls.py`. The existing `/api/recommendations/` returns a list of 10 tracks; the daily gem endpoint needs one track with an explanation and a `score_breakdown`.

```python
# Source: direct codebase inspection — DailyGem model, views.py patterns
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_gem(request):
    force_new = request.GET.get('force_new', 'false').lower() == 'true'
    today = timezone.localdate()

    # Return cached gem unless force_new
    if not force_new:
        existing_gem = DailyGem.objects.filter(user=request.user, date=today).first()
        if existing_gem:
            return JsonResponse({
                'track': {
                    'id': existing_gem.track.spotify_id,
                    'name': existing_gem.track.name,
                    'artist': existing_gem.track.artist,
                    'album': existing_gem.track.album,
                    'popularity': existing_gem.track_popularity,
                    'image_url': existing_gem.image_url,
                    'preview_url': existing_gem.preview_url,
                },
                'explanation': existing_gem.explanation,
                'date': str(today),
                'cached': True,
                'score_breakdown': None  # or store in DailyGem if needed
            })

    # Generate fresh gem
    engine = HybridRecommendationEngine(request.user)
    recs = engine.get_recommendations(limit=20, force_fresh=force_new)
    # pick top track, generate explanation, create DailyGem record
    # ...
```

**URL addition required in `config/urls.py`:**
```python
path('api/daily-gem/', views.get_daily_gem, name='daily_gem'),
```

### Anti-Patterns to Avoid

- **Reading `track_info` dict for genres in `apply_feedback_learning`:** The `track_info` dict passed via `add_feedback()` has only `artist`, `name`, `album` — NO `genres` key. Use `feedback.track.genres` instead (the `Track` ORM field, already populated via `sp.artist()` call in `submit_feedback` on track creation).
- **Calling `update_weights()` from `PersonalizationEngine`:** `UserProfile.update_weights(weights)` takes only one argument (`weights`). `PersonalizationEngine` does not hold `self.profile`. Fetch `UserProfile` directly: `UserProfile.objects.get(user=self.user)`.
- **Assuming `_score_recommendations` already uses `get_recommendation_weights()`:** It does not. The method is only called from `get_profile_summary()`. Any bandit integration into scoring requires explicit wiring.
- **Calling `get_recommendation_weights()` outside the engine scope:** It's a `UserProfile` method that returns a static dict. Phase 3 replaces this method or overrides its return value via bandit sampling — the bandit sampling belongs in `HybridRecommendationEngine`, not in `UserProfile`.
- **Storing `score_breakdown` in `DailyGem` model:** `DailyGem` has no `score_breakdown` field. Either return it from the view without persisting, or add the field. Adding a field requires a migration. Returning without persisting is simpler and the CONTEXT.md D-14 says "Frontend can display or ignore for now."

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Beta distribution sampling | Manual inverse-CDF | `numpy.random.beta(a, b)` | Verified at numpy 2.1.3; one-liner; numerically stable |
| Gaussian bell curve | Lookup table | `math.exp(-x**2/(2*s**2))` | stdlib, no install; 1 line; correct |
| JSON persistence | Custom serialization | Django JSONField `profile.save(update_fields=['data'])` | Established pattern across all prior phases |
| OpenAI client | Direct `requests` calls | `openai.OpenAI` client (already in `FeedbackInterpreter`) | Rate limiting, retries, typed responses already wired |

**Key insight:** All state management follows the same JSONField mutation pattern used in `UserProfile.add_feedback()`. Do not create new models or migrations for bandit state — it lives in `UserProfile.data['source_stats']`.

---

## Common Pitfalls

### Pitfall 1: `track_info` Dict Missing `genres` Key
**What goes wrong:** `apply_feedback_learning` tries to read `genres` from `track_info` stored in `feedback_history`. The dict stored there has `artist`, `name`, `album` only — no `genres`.
**Why it happens:** `submit_feedback` builds `track_info = {'artist': track.artist, 'name': track.name, 'album': track.album}` at line 508 — `genres` was intentionally omitted.
**How to avoid:** Read genres from `feedback.track.genres` — the `UserFeedback` object already has `track` FK. `Track.genres` is a `JSONField(default=list)` populated at track creation.
**Warning signs:** `taste_vector` never updates despite feedback being submitted.

### Pitfall 2: `PersonalizationEngine` Has No `self.profile`
**What goes wrong:** Implementation accesses `self.profile.data` inside `apply_feedback_learning`, but `PersonalizationEngine.__init__` only sets `self.user` and `self.preferences` (a `UserPreferences` object, not `UserProfile`).
**Why it happens:** The two engines are separate classes. `UserProfile` and `UserPreferences` are separate models.
**How to avoid:** `from apps.core.models import UserProfile; profile = UserProfile.objects.get(user=self.user)` at the top of each method that needs it.
**Warning signs:** `AttributeError: 'PersonalizationEngine' object has no attribute 'profile'`.

### Pitfall 3: `_score_recommendations` Does Not Currently Read Source Weights
**What goes wrong:** D-08 states "zero changes to scoring code" — but this assumes `_score_recommendations` already consumes `get_recommendation_weights()`. It does not.
**Why it happens:** Phase 2 CONTEXT.md described the intended design, but the actual implementation only uses the three-component formula. `get_recommendation_weights()` is only called in `get_profile_summary()`.
**How to avoid:** Add one line in `_score_recommendations()` to call `get_recommendation_weights()` and apply the returned `source_weight` as a post-score multiplier: `rec['score'] *= source_weight.get(rec.get('source', ''), 1.0)`.
**Warning signs:** Bandit state updates but recommendations don't change.

### Pitfall 4: `genre_search` Source Has No Candidate Generation Method
**What goes wrong:** `RecommendationLog.source` includes `'genre_search'` as a valid choice, but there is no `_get_genre_search_recommendations()` method in `HybridRecommendationEngine`.
**Why it happens:** The source choice was added in Phase 2 migration for completeness; the implementation strategy was never built.
**How to avoid:** The bandit initializes `source_stats` for all 5 sources including `genre_search`. Since `genre_search` never produces candidates, its `s` and `f` counts stay at 0 and it stays in cold-start mode (uses static weight). This is safe — the planner should document this as known behavior, not a bug.
**Warning signs:** Bandit weight for `genre_search` is always the static fallback.

### Pitfall 5: `DailyGem` Has No `score_breakdown` Field
**What goes wrong:** Attempt to persist `score_breakdown` to `DailyGem` model fails — no such column.
**Why it happens:** `DailyGem` model (`models.py` line 280) has `explanation`, `image_url`, `preview_url`, `track_popularity`, `was_liked`, `was_skipped` — no `score_breakdown`.
**How to avoid:** Either (a) return `score_breakdown` in the API response without persisting (lose it on refresh), or (b) add a `score_breakdown = models.JSONField(default=dict, blank=True)` field + migration. Option (b) is needed if Phase 4 wants historical score breakdowns. For Phase 3, option (a) is simpler.
**Warning signs:** `FieldError` when trying to `DailyGem.objects.create(score_breakdown=...)`.

### Pitfall 6: `openai` Not in Project Venv
**What goes wrong:** `RecommendationExplainer.generate_explanation()` silently falls back to a stub because `openai` import fails.
**Why it happens:** `openai` is not installed in `backend/venv/`. The `FeedbackInterpreter` in `ai_feedback_service.py` already handles this gracefully — it catches `ImportError` and sets `self.openai_client = None`.
**How to avoid:** Wave 0 task: `cd backend && venv/bin/pip install openai`. Or, `RecommendationExplainer` can use a rule-based fallback explanation for testing.
**Warning signs:** Explanation is always the same generic string regardless of score breakdown.

### Pitfall 7: `remove_feedback_learning` Receives `track_id` (str), Not `UserFeedback`
**What goes wrong:** Unlike path passes `track.spotify_id` (a string), not a `UserFeedback` object. The unlike logic must look up genres from `Track.objects.filter(spotify_id=track_id)`.
**Why it happens:** The unlike branch in `submit_feedback` deletes `existing_feedback` before calling `remove_feedback_learning`, so the feedback object is gone.
**How to avoid:** Fetch `Track` by `spotify_id` inside `remove_feedback_learning()`. The method signature `remove_feedback_learning(self, track_id: str)` already reflects this — `Track` is in the same app and queryable by `spotify_id`.

---

## Code Examples

### Thompson Sampling: One-Liner Beta Sample

```python
# Source: numpy 2.1.3 docs, verified in backend venv
import numpy as np
sample = float(np.random.beta(s + 1, f + 1))  # always > 0, no division by zero
```

### Gaussian Bell-Curve Novelty

```python
# Source: Python stdlib math docs — no install needed
import math
def bell_curve_novelty(popularity: int, midpoint: float, width: float) -> float:
    return math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))
# At midpoint: returns 1.0 (maximum novelty match)
# At midpoint ± width: returns ~0.6
# At midpoint ± 2*width: returns ~0.135
```

### Popularity Midpoint Update (D-12)

```python
# lr=0.1 exponential moving average toward track's popularity
# Like: midpoint moves toward track's popularity
# Dislike: midpoint moves away from track's popularity
midpoint += 0.1 * (track_popularity - midpoint) * signal  # signal: +1 like, -1 dislike
```

### Initialize `source_stats` (cold start)

```python
# Source: D-07 from CONTEXT.md + JSONField pattern from models.py
DEFAULT_SOURCES = ['playlist_mining', 'artist_network', 'genre_search',
                   'related_artists', 'contextual']

def _default_source_stats():
    return {src: {'s': 0, 'f': 0} for src in DEFAULT_SOURCES}

# Usage: source_stats = profile.data.setdefault('source_stats', _default_source_stats())
```

### `score_breakdown` Response Format (D-14)

```python
# Source: CONTEXT.md D-14
score_breakdown = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'top_genres': sorted(taste_vector, key=taste_vector.get, reverse=True)[:3]
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static source weights (hardcoded dict) | Thompson Sampling per-source Beta posterior | Phase 3 | Bandit adapts weights to actual win rates |
| `novelty = 1 - pop/100` (linear, fixed) | Bell-curve novelty centered on learned midpoint | Phase 3 | Novelty score peaks at user's preferred popularity level |
| No-op `apply_feedback_learning` | Online SGD on taste vector + midpoint update | Phase 3 | Recommendations improve after each like/dislike |
| No `/api/daily-gem/` endpoint | New Django view + DailyGem persistence | Phase 3 | Frontend daily gem component actually works |

**Note on "genre_search" source:** It is listed in `RecommendationLog.source` choices and initialized in `source_stats`, but no `_get_genre_search_recommendations()` method exists. Its bandit arm will stay in cold-start indefinitely. This is harmless but should be documented in `CONCEPTS.md` (Phase 4).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `feedback.track.genres` is populated for all tracked feedback events because `submit_feedback` calls `sp.artist()` on track creation | Pitfall 1, Pattern 1 | If a track was created before Phase 1 (when `genres` may have been empty), genres list could be `[]`, causing no taste vector update for that feedback | [VERIFIED: views.py line 449 `track.genres = artist_info['genres']` is in the `if created:` block — only runs on first encounter] |
| A2 | `remove_feedback_learning` is always called before `hybrid_engine.remove_feedback` in the unlike path, so `feedback_history` still has the entry | Pattern 4 | If history was already cleared, unlike reversal silently no-ops | [VERIFIED: views.py unlike path: `personalization_engine.remove_feedback_learning(track.spotify_id)` at line 467 runs before `hybrid_engine.remove_feedback(track.spotify_id)` at line 471] |
| A3 | `RecommendationLog.source` is reliably populated for all recommendations from Phase 2 onward | Pattern 5, Pitfall 4 | If source is blank (`''`), bandit credit lookup returns `None` and the source stat doesn't update | [VERIFIED: views.py line 336 passes `source=track.get('source', '')` — empty string if source missing, bandit should guard `if source:` before updating stats] |

**If this table is empty:** All claims were verified — no user confirmation needed. (A1–A3 above are verified by direct code inspection; no assumed claims.)

---

## Open Questions

1. **Should `score_breakdown` be persisted to `DailyGem`?**
   - What we know: `DailyGem` model has no `score_breakdown` field. Phase 4 wants metrics visualization.
   - What's unclear: Whether Phase 4 needs historical score breakdowns per gem, or just the current gem's breakdown.
   - Recommendation: Add `score_breakdown = models.JSONField(default=dict, blank=True)` to `DailyGem` + migration in Wave 0. Small cost now, enables Phase 4 metrics.

2. **Should the bandit `source_weight` be a multiplier or additive?**
   - What we know: The locked formula is additive. CONTEXT.md says the bandit replaces `get_recommendation_weights()` which currently isn't used in scoring.
   - What's unclear: Whether `score = locked_formula * source_weight` or `score = locked_formula + source_component` better matches the user's intent.
   - Recommendation: Multiplicative post-score (`score *= source_weight`) — preserves the locked additive formula and lets the bandit act as a confidence scaling factor without changing the formula semantics.

3. **Where should `_get_source_for_track` live?**
   - What we know: It needs to be called from `apply_feedback_learning` (in `PersonalizationEngine`) but it queries `RecommendationLog`.
   - What's unclear: Whether this is a static helper, a `PersonalizationEngine` method, or a `RecommendationLog` class method.
   - Recommendation: Make it a `RecommendationLog` class method: `RecommendationLog.get_source_for_user_track(user, track)`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `numpy` | Thompson Sampling Beta sampling | Yes | 2.1.3 (in venv) | None needed |
| `math` (stdlib) | Gaussian bell curve | Yes | stdlib | None needed |
| `openai` Python SDK | `RecommendationExplainer` | No (missing from venv) | — | Rule-based fallback explanation |
| Django + DRF | `/api/daily-gem/` view | Yes | existing | — |
| SQLite | `DailyGem`, `RecommendationLog` | Yes | existing | — |

**Missing dependencies with no fallback:** None that block core learning loop.

**Missing dependencies with fallback:**
- `openai`: `RecommendationExplainer` falls back to rule-based explanation template. Install with `backend/venv/bin/pip install openai` to enable real GPT-4o-mini explanations.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 (system Python), pytest-django via `conftest.py` |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=$(pwd) python3 -m pytest tests/test_feedback_learning.py -x -q` |
| Full suite command | `cd backend && DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=$(pwd) python3 -m pytest tests/ -q --ignore=tests/test_ai_feedback_service.py --ignore=tests/test_openai_integration.py` |

**Current baseline:** 44 of 55 tests pass (8 fail due to missing `openai` package — pre-existing, not Phase 3 regressions). Phase 3 should not break the 44 passing tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | `apply_feedback_learning` updates `taste_vector` on LIKE | unit | `pytest tests/test_feedback_learning.py::TestTasteVectorUpdate::test_like_increments_genre -x` | No — Wave 0 |
| D-01 | `apply_feedback_learning` updates `taste_vector` on DISLIKE | unit | `pytest tests/test_feedback_learning.py::TestTasteVectorUpdate::test_dislike_decrements_genre -x` | No — Wave 0 |
| D-04 | `remove_feedback_learning` reverses taste vector update | unit | `pytest tests/test_feedback_learning.py::TestTasteVectorUndo::test_unlike_reverses_genre -x` | No — Wave 0 |
| D-06/D-07 | `apply_feedback_learning` increments `source_stats['s']` on LIKE | unit | `pytest tests/test_feedback_learning.py::TestBanditState::test_like_increments_success -x` | No — Wave 0 |
| D-07 | `source_stats` initializes cold-start schema if absent | unit | `pytest tests/test_feedback_learning.py::TestBanditState::test_cold_start_init -x` | No — Wave 0 |
| D-08 | `get_recommendation_weights()` returns Beta samples after cold start | unit | `pytest tests/test_feedback_learning.py::TestBandit::test_weights_after_cold_start -x` | No — Wave 0 |
| D-10 | Bell-curve novelty peaks at `midpoint` | unit | `pytest tests/test_feedback_learning.py::TestNovelty::test_bell_curve_peaks_at_midpoint -x` | No — Wave 0 |
| D-12 | Like shifts `midpoint` toward track popularity | unit | `pytest tests/test_feedback_learning.py::TestPopularityRange::test_like_shifts_midpoint -x` | No — Wave 0 |
| D-14 | `/api/daily-gem/` returns `score_breakdown` in response | integration | `pytest tests/test_feedback_learning.py::TestDailyGemView::test_response_includes_score_breakdown -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_feedback_learning.py -x -q`
- **Per wave merge:** Full suite (excluding openai tests)
- **Phase gate:** Full suite (44+ passing) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_feedback_learning.py` — covers D-01 through D-14 (all Phase 3 requirements)
- [ ] Framework install: `cd backend && venv/bin/pip install openai` — if explanation tests needed

---

## Security Domain

> `security_enforcement` not set in config — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — no new auth routes | — |
| V3 Session Management | No — uses existing session | — |
| V4 Access Control | Yes — new `/api/daily-gem/` view | `@permission_classes([IsAuthenticated])` — required, same as existing views |
| V5 Input Validation | Yes — `force_new` query param | `request.GET.get('force_new', 'false').lower() == 'true'` — string comparison only, safe |
| V6 Cryptography | No — no new crypto | — |

### Known Threat Patterns for Django REST + JSONField

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| JSONField injection via feedback | Tampering | Values come from `feedback.track.genres` (DB field) and `feedback.feedback_type` (validated choices) — no user-supplied strings injected into JSONField keys |
| Source stats manipulation | Tampering | `source_stats` keys validated against `BANDIT_SOURCES` list before write — reject unknown sources |
| Daily gem replay / force_new abuse | Denial of Service | `/api/daily-gem/?force_new=true` triggers full Spotify API fetch — existing rate limiting in `rate_limit_monitor` applies |

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `backend/apps/recommendations/hybrid_recommendation_engine.py` — `_score_recommendations()`, `add_feedback()`, `remove_feedback()`, `get_recommendation_weights()` — all verified by reading
- `backend/apps/recommendations/personalization_engine.py` — `apply_feedback_learning()` (lines 251–268), `remove_feedback_learning()` (lines 270–281) — confirmed no-ops
- `backend/apps/core/models.py` — `UserProfile.data` JSONField schema, `UserFeedback` choices, `Track.genres`, `DailyGem` fields, `RecommendationLog.source` — all verified
- `backend/apps/core/views.py` — `submit_feedback` (lines 408–541), `track_info` construction (lines 508–512), `apply_feedback_learning` call (line 504) — verified
- `backend/config/urls.py` — confirmed `/api/daily-gem/` route is absent
- `numpy 2.1.3` — verified in venv, `numpy.random.beta` confirmed working

### Secondary (MEDIUM confidence)
- CONTEXT.md D-01 through D-14 — user decisions, locked as planning inputs
- ROADMAP.md Phase 3 — deliverables list cross-referenced with codebase state

### Tertiary (LOW confidence)
- None — all key claims verified by direct code inspection this session.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — numpy verified in venv; openai absence verified
- Architecture: HIGH — all integration points verified by reading actual code; no-ops confirmed; `track_info` gap discovered
- Pitfalls: HIGH — discovered by direct inspection (track_info missing genres, PersonalizationEngine lacks self.profile, _score_recommendations doesn't use weights)

**Research date:** 2026-05-11
**Valid until:** 2026-06-10 (30 days; stable Django codebase)

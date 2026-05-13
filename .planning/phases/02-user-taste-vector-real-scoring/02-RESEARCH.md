# Phase 2: User Taste Vector & Real Scoring - Research

**Researched:** 2026-05-07
**Domain:** Content-based filtering, cosine similarity scoring, Django model migrations
**Confidence:** HIGH — all findings verified against actual source files

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Data source is `top_artists` only — already fetched in `_update_profile_data()`. No extra Spotify API calls.
- **D-02:** Weighting is flat count — each genre occurrence on each artist adds 1.0. No TF-IDF.
- **D-03:** Stored as raw counts: `UserProfile.data['taste_vector'] = {"indie rock": 7, "folk": 4, ...}`. Not pre-normalized. Human-readable.
- **D-04:** Vector rebuilds inside `_update_profile_data()` alongside the top_artists fetch.
- **D-05:** `genre_sim` = cosine similarity between candidate track's artist genres and `UserProfile.data['taste_vector']`.
- **D-06:** `novelty` = `1 - (popularity / 100)`. Use `popularity` field already on recommendation dicts.
- **D-07:** `feedback_multiplier` = artist-level liked/disliked signal from `UserProfile.data['preferences']['liked_artists']` and `disliked_artists`. Proper 0.3-weighted component.
- **D-08:** Delete `_update_weights_from_ai_feedback()` (line 898 of hybrid_recommendation_engine.py).
- **D-09:** Remove `tempo_weight`, `energy_weight`, `valence_weight` from recommendation_weights. `add_ai_feedback()` stops calling `_update_weights_from_ai_feedback()` — rest of method (storing AI feedback history) stays.
- **D-10:** Add `source = CharField(max_length=50, choices=[...], blank=True, default='')` to `RecommendationLog`. One Django migration. Source values: `playlist_mining`, `artist_network`, `genre_search`, `related_artists`, `contextual`.
- **D-11:** Cold-start fallback: if source has fewer than N logged recommendations, fall back to existing static weights. Planner decides N.
- **Score formula (ROADMAP locked):** `score = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`

### Claude's Discretion
- Cold-start threshold N for per-strategy win-rate — planner chooses (suggested: 5 per source).
- Whether `Track.genres` is already populated in DB or needs live `sp.artist()` lookup at score time — **researcher to check** (see findings below).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 2 replaces the ad hoc scoring heuristic in `_score_recommendations()` (lines 717-748) with a real content-based formula. All three formula inputs are available without new API calls: genre similarity requires either a DB lookup (Track.genres field exists but is only populated for tracks that have gone through the `submit_feedback` code path) or a genres-bearing artist-level dict already in `base_data['top_artists']`; novelty uses `popularity` already in every recommendation dict; feedback_multiplier uses `liked_artists` / `disliked_artists` already in `profile.data['preferences']`. The taste vector is built from `base_data['top_artists'][*]['genres']` which is already fetched and stored on every profile refresh.

The primary gap is that recommendation candidate dicts do NOT carry genres — genres live in `Track.genres` (DB model) or in a separate `sp.artist()` call. The resolution strategy is covered in the Track.genres section below. scipy is available in the project environment (verified), and numpy is already imported in the engine file. Migration pattern is established across 5 prior migrations — all follow `migrations.AddField` with no custom operations needed for a simple CharField.

**Primary recommendation:** Implement cosine similarity using pure numpy on dict-based vectors (no scipy import needed); genres for score-time lookup come from `base_data['top_artists']` dict keyed by artist name as the zero-API-call path.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Taste vector build | API / Backend (engine) | — | `_update_profile_data()` runs server-side on profile refresh |
| Genre similarity scoring | API / Backend (engine) | — | `_score_recommendations()` is internal to HybridRecommendationEngine |
| Novelty calculation | API / Backend (engine) | — | Pure arithmetic on `popularity` field already in recommendation dict |
| Feedback multiplier | API / Backend (engine) | — | Reads from `UserProfile.data['preferences']` — server-side only |
| RecommendationLog.source write | API / Backend (views) | — | Single call site in views.py:336 |
| Win-rate query | API / Backend (engine) | — | Inside `_score_recommendations()`, reads from DB before static fallback |
| Migration | Database / Storage | — | Standard Django `manage.py makemigrations` |

---

## Q1: Track.genres Availability — CRITICAL FINDING

**Question:** Is `Track.genres` populated in the DB for most recommendation candidates, or does scoring need a live `sp.artist()` call?

**Finding:** `Track.genres` is a `JSONField(default=list)` added in migration `0003` (verified: `backend/apps/core/migrations/0003_track_genres_userfeedback_feedback_type_and_more.py`). Genres are populated in exactly ONE code path: `views.py:submit_feedback` at lines 554-562, which calls `sp.artist()` only when a `Track` object is `created=True` (i.e., first time a user gives feedback on that track).

**Consequence:** For the vast majority of recommendation candidates, `Track.genres` is an empty list `[]` in the DB. Candidate dicts built by `_get_playlist_recommendations()`, `_get_artist_network_recommendations()`, `_get_contextual_recommendations()`, and `_get_related_artist_recommendations()` do NOT include a `genres` key — they only carry `id`, `name`, `artist`, `album`, `preview_url`, `image_url`, `source`, `score`, `popularity`. [VERIFIED: grep of all four strategy methods — none attach genres to the rec dict]

**Resolution path (zero extra API calls):** The taste vector is built from `base_data['top_artists']` which already stores `{'id': ..., 'name': ..., 'genres': [...], 'popularity': ...}` per artist (verified: `hybrid_recommendation_engine.py:270-278`). The scoring function can look up genres by artist name in this dict. At score time:

```python
# Build artist -> genres lookup from already-fetched top_artists data
artist_genre_lookup = {
    a['name']: a['genres']
    for a in self.profile.data.get('base_data', {}).get('top_artists', [])
}
candidate_genres = artist_genre_lookup.get(rec['artist'], [])
```

This covers candidates from `artist_network` and `related_artists` strategies (artists are adjacent to/related to the user's top artists so many will appear). For `playlist_mining` and `contextual` candidates whose artist is not in the lookup, `candidate_genres` will be `[]`, which produces a `genre_sim` of `0.0` — that is the correct behavior (unknown genre alignment = no similarity boost).

**Alternative considered (DB lookup):** `Track.objects.filter(spotify_id=rec['id']).values_list('genres', flat=True).first()` — adds N DB queries per scoring call (one per candidate). With 60-100 candidates per `get_recommendations()` call, this is an unacceptable N+1. Reject.

**Alternative considered (live sp.artist()):** Adds 1 Spotify API call per candidate at score time. With 60-100 candidates, this would exhaust the rate limit budget before scoring completes. Reject.

**Verdict:** Use artist-name lookup in `base_data['top_artists']` dict. Zero extra calls. Graceful degradation for out-of-catalog artists (score 0.0 on genre_sim, formula still applies novelty and feedback components). [VERIFIED: base_data structure]

---

## Q2: Cosine Similarity Implementation

**Question:** numpy manually or `scipy.spatial.distance.cosine`?

**scipy availability:** scipy 1.11.4 is installed in the backend environment (verified: `python3 -c "import scipy; print(scipy.__version__)"`). However, it is NOT in `requirements.txt` (which only lists Django, DRF, spotipy, requests, dotenv, openai). [VERIFIED: `backend/requirements.txt`]

**numpy availability:** numpy 1.26.4 is installed. `import numpy as np` is already at line 12 of `hybrid_recommendation_engine.py`. [VERIFIED: line 12 of engine file]

**Recommendation: Use pure numpy (no scipy import).** Adding scipy as an implicit dependency without adding it to requirements.txt is a maintenance hazard. The cosine similarity operation on dict-based vectors is 4 lines with numpy and does not benefit from scipy's optimization at these small vector sizes (max ~1000 unique Spotify genres).

**Pattern for dict-based vectors:**

```python
# Source: numpy docs — standard cosine similarity implementation
def _cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    """
    Cosine similarity between two genre count dicts.
    Returns 0.0 if either vector is empty or zero-magnitude.
    """
    if not vec_a or not vec_b:
        return 0.0
    keys = set(vec_a.keys()) | set(vec_b.keys())
    a = np.array([vec_a.get(k, 0.0) for k in keys])
    b = np.array([vec_b.get(k, 0.0) for k in keys])
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
```

**Input shapes:**
- `vec_a`: candidate genres as `{genre: 1.0}` (flat presence, not counts — candidate tracks have a genre list, not counts)
- `vec_b`: `UserProfile.data['taste_vector']` = `{"indie rock": 7, "folk": 4, ...}` (raw counts, not normalized — cosine normalizes at call time per D-03)

**Edge cases to handle:**
- Empty taste vector (new user, no top_artists fetched yet) → return 0.0
- Candidate artist not in artist_genre_lookup → `candidate_genres = []` → return 0.0
- All genres in candidate not in user vector → dot product = 0.0 → return 0.0 (correct)

[ASSUMED: scipy is not required to be in requirements.txt — verify before adding it as an import]

---

## Q3: Current `_score_recommendations()` — Full Implementation

**Location:** `hybrid_recommendation_engine.py` lines 717-748 [VERIFIED]

**Current implementation (verbatim):**

```python
def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
    """Score recommendations based on user profile and preferences"""
    weights = self.profile.get_recommendation_weights()
    liked_artists = self.profile.data['preferences'].get('liked_artists', [])
    disliked_artists = self.profile.data['preferences'].get('disliked_artists', [])
    
    for rec in recommendations:
        score = 0.0
        
        # Base score from source
        source_weight = weights.get(rec['source'], 0.1)
        score += source_weight
        
        # Artist preference bonus
        if rec['artist'] in liked_artists:
            score += weights['feedback'] * 2  # Double the feedback weight
        elif rec['artist'] in disliked_artists:
            score -= weights['feedback'] * 3  # Heavy penalty for disliked artists
        
        # Contextual bonus
        if rec['source'] == 'contextual':
            score += weights['contextual'] * 0.5
        
        # Playlist mining bonus (hidden gems)
        if rec['source'] == 'playlist_mining':
            score += weights['playlist_mining'] * 0.3
        
        rec['score'] = max(0.0, score)  # Ensure non-negative score
    
    # Sort by score (highest first)
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations
```

**Input:** `List[Dict]` — each dict has keys: `id`, `name`, `artist`, `album`, `preview_url`, `image_url`, `source`, `score` (initially 0.0 or 0.3 for contextual), `popularity`.

**Output:** Same `List[Dict]` — mutates `rec['score']` in-place, then sorts in-place, returns sorted list.

**What the replacement must preserve:**
- Same function signature: `(self, recommendations: List[Dict]) -> List[Dict]`
- Mutates `rec['score']` on each dict
- Returns list sorted descending by `score`
- Called at line 144: `scored_recommendations = self._score_recommendations(unique_recommendations)`
- No other callers — one call site [VERIFIED: grep shows single call]

**What changes:**
- Drop the ad hoc source_weight base + contextual/playlist_mining bonuses
- Replace with formula: `score = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`
- genre_sim: cosine similarity (new `_cosine_similarity` helper)
- novelty: `1 - (popularity / 100)` — `popularity` is already in every rec dict [VERIFIED]
- feedback_multiplier: liked artist → positive, disliked → negative (see D-07 specifics below)

**feedback_multiplier specifics:** The current code uses `weights['feedback'] * 2` and `weights['feedback'] * 3`. The new formula replaces this with a fixed 0.3 component. Suggested values: liked artist → `1.0`, disliked artist → `0.0` (floor), neither → `0.5` (neutral). This keeps the multiplier in [0, 1] so the 0.3 weight is never overcounted. [ASSUMED: specific liked/disliked/neutral values — planner should confirm 1.0/0.5/0.0 or adjust]

---

## Q4: Django Migration Pattern

**Verified pattern** from the 5 existing migrations in `backend/apps/core/migrations/`:

**Migration naming convention:** Auto-generated by Django. File names follow:
- `0001_initial.py`
- `0002_userprofile_data.py`
- `0003_track_genres_userfeedback_feedback_type_and_more.py`
- `0004_recommendationlog_track_popularity_and_more.py`
- `0005_dailygem_image_url_dailygem_preview_url.py`

Next migration will be: `0006_recommendationlog_source.py` (generated automatically).

**Exact command to run:**
```bash
cd backend
python manage.py makemigrations core --name recommendationlog_source
python manage.py migrate
```

**Model change to make first** (in `backend/apps/core/models.py`, `RecommendationLog` class, after `was_novel` field):
```python
source = models.CharField(
    max_length=50,
    choices=[
        ('playlist_mining', 'Playlist Mining'),
        ('artist_network', 'Artist Network'),
        ('genre_search', 'Genre Search'),
        ('related_artists', 'Related Artists'),
        ('contextual', 'Contextual'),
    ],
    blank=True,
    default='',
)
```

**What the generated migration will contain** (based on verified pattern in 0003, 0004, 0005):
```python
migrations.AddField(
    model_name="recommendationlog",
    name="source",
    field=models.CharField(
        blank=True,
        choices=[...],
        default='',
        max_length=50,
    ),
),
```

[VERIFIED: migration pattern from 0003, 0004, 0005 files]

---

## Q5: `RecommendationLog.log_recommendation()` — All Call Sites

**Definition:** `backend/apps/core/models.py` lines 242-248

**Current signature:**
```python
@classmethod
def log_recommendation(cls, user, track):
    """Log a track recommendation"""
    try:
        cls.objects.create(user=user, track=track)
    except Exception as e:
        logger.error(f"Error logging recommendation: {str(e)}")
```

**Call sites (grep verified — exactly ONE call site):**

| File | Line | Context |
|------|------|---------|
| `backend/apps/core/views.py` | 336 | Inside `get_track_recommendations()` view, after processing recommendation dicts |

**Call site code:**
```python
# views.py lines 327-336
for track in processed_tracks:
    track_obj = Track.objects.get_or_create(
        spotify_id=track['id'],
        defaults={
            'name': track.get('name', ''),
            'artist': track.get('artist', ''),
            'album': track.get('album', ''),
        }
    )[0]
    RecommendationLog.log_recommendation(request.user, track_obj)
```

**What changes for Phase 2:** The `source` field must be passed. Two options:

Option A — Add `source` parameter to `log_recommendation` class method:
```python
@classmethod
def log_recommendation(cls, user, track, source=''):
    cls.objects.create(user=user, track=track, source=source)
```
Then the call site becomes:
```python
RecommendationLog.log_recommendation(request.user, track_obj, source=track.get('source', ''))
```

Option B — Update call site to use `cls.objects.create()` directly with source.

**Recommendation: Option A** — preserves the class method abstraction, backward-compatible (default `source=''`), minimal diff at the single call site. [ASSUMED: no other call sites exist — verified by grep but could be in test files calling it directly; grep confirms test files do `RecommendationLog.objects.create()` directly, not via `log_recommendation`]

[VERIFIED: single call site at views.py:336]

---

## Q6: `personalization_engine._calculate_feature_preferences()` — Dead Code Verdict

**Finding: CONFIRMED DEAD CODE** — returns defaults unconditionally. [VERIFIED: personalization_engine.py lines 84-92]

**Current implementation:**
```python
def _calculate_feature_preferences(self, feature: str, positive_feedback, negative_feedback) -> Dict:
    """
    Calculate preference ranges for a specific audio feature.
    
    Since we can't get audio features from Spotify API, we'll use default preferences
    and learn from user feedback patterns instead.
    """
    # For now, return default preferences since we can't get audio features
    return self._get_default_feature_preferences(feature)
```

The function accepts `positive_feedback` and `negative_feedback` querysets but ignores them entirely, returning only hardcoded defaults. Since `sp.audio_features` is deprecated and `track_features` is never populated (views.py:610: `track_features={}`), this will remain permanently broken.

**Call chain:**
- `analyze_user_preferences()` (line 41) calls `_calculate_feature_preferences()` for each audio feature
- `analyze_user_preferences()` is called by:
  - `get_personalization_summary()` in `personalization_engine.py` (line 290)
  - `track_discovery_engine.py` (line 56) via `self.personalization_engine.analyze_user_preferences()`
  - `get_personalization_summary` view endpoint in `views.py` (line 365)

**Decision for Phase 2:** The CONTEXT.md says to "verify whether this is also dead code" — it is. However, CONTEXT.md's D-08/D-09 only specify deleting `_update_weights_from_ai_feedback()` and its three weight keys. The `_calculate_feature_preferences()` chain is separate from the scoring path. The planner should decide whether to:
1. Leave it (it's harmless — returns defaults, wastes ~5 lines of execution)
2. Delete it (cleaner, but `analyze_user_preferences()` would break callers)
3. Convert to a no-op stub (safest — keeps callers working, signals intent)

**Recommendation: Leave for a separate cleanup phase.** Deleting `analyze_user_preferences()` cascades to `track_discovery_engine.py` and `views.py` — out of Phase 2 scope. [ASSUMED: planner will defer personalization_engine dead code cleanup]

---

## Q7: Existing Test Patterns from Phase 1

**Test infrastructure** (all verified by reading files):

**`backend/tests/conftest.py`** — Minimal Django setup:
- `sys.path.insert(0, backend_dir)` to resolve `apps.*` imports
- `DJANGO_SETTINGS_MODULE = 'config.settings'`
- `django.setup()` call
- No shared fixtures — each test class has its own `setUp()`

**Two test base patterns used in Phase 1:**

**Pattern A: `django.test.TestCase` (DB-backed)**
Used in: `test_recommendation.py`, `test_feedback.py`
```python
class TestPersistentExclusionSet(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('exuser', password='pw')
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'data': {'base_data': {'top_artists': []}, 'preferences': {}}},
        )
        self.track = Track.objects.create(
            spotify_id='some_id',
            name='Track Name',
            artist='Artist',
            album='Album',
        )
        RecommendationLog.objects.create(user=self.user, track=self.track)

    def test_something(self):
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        # ...assertions
```

**Pattern B: `unittest.TestCase` with `Mock`/`patch` (no DB)**
Used in: `test_recommendation.py`, `test_personalization.py`
```python
class TestRelatedArtistStrategy(unittest.TestCase):
    def test_returns_candidates_on_valid_api_response(self):
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {
            'base_data': {'top_artists': [...]},
            'preferences': {'liked_artists': [], 'disliked_artists': []},
        }
        with patch.object(engine, '_get_spotify_client', return_value=mock_sp), \
             patch.object(engine, '_check_rate_limit', return_value=True):
            results = engine._some_method(limit=5)
        self.assertEqual(results[0]['source'], 'expected_source')
```

**Key detail for Phase 2 tests:** `HybridRecommendationEngine.__new__(HybridRecommendationEngine)` bypasses `__init__()` (which tries to DB-connect). This is the correct pattern for testing scoring logic without a real DB or Spotify token.

**For scoring function tests** (Pattern B is ideal):
- Set `engine.profile.data = {'taste_vector': {...}, 'preferences': {'liked_artists': [...], ...}}`
- Pass crafted recommendation dicts directly to `engine._score_recommendations(recs)`
- Assert on `rec['score']` values — no mocking needed for the pure scoring logic

**Test runner command:**
```bash
cd backend && python -m pytest tests/ -v
```
(verified from `tests/README.md` pattern and Phase 1 plan execution)

---

## Q8: Cold-Start Win-Rate Placement Recommendation

**Question:** Where exactly does the per-strategy win-rate lookup belong — inside `_score_recommendations()` or in `get_recommendation_weights()`?

**Current flow analysis:**
1. `_score_recommendations()` (line 717) calls `self.profile.get_recommendation_weights()` (line 719) to get static weights dict
2. Uses `weights.get(rec['source'], 0.1)` as the base score per candidate
3. Phase 2 formula **removes** this source-weight-as-base-score pattern — the formula is `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier`

**Implication:** The per-strategy win-rate from D-11 is NOT part of the Phase 2 scoring formula. The formula in CONTEXT.md uses no source weight component at all. The D-11 cold-start behavior is for future Phase 3 bandit logic — win-rate will replace static weights when Phase 3 introduces per-source success tracking.

**For Phase 2 specifically:** The `source` field is being added to `RecommendationLog` so that win-rate tracking CAN happen in Phase 3. Phase 2 just needs to write `source` to the log (the `log_recommendation()` call site in views.py). No win-rate query is needed in Phase 2 scoring — the formula has no source-weight term.

**If the planner interprets D-11 as a Phase 2 deliverable:** The placement should be inside `_score_recommendations()` as a pre-pass before applying the formula. The lookup pattern:
```python
def _get_source_win_rate(self, source: str, min_count: int = 5) -> float:
    """Return win rate for source if enough data, else None (triggers static fallback)."""
    from apps.core.models import RecommendationLog
    logs = RecommendationLog.objects.filter(user=self.user, source=source)
    total = logs.count()
    if total < min_count:
        return None  # cold-start: not enough data
    liked = logs.filter(liked=True).count()
    return liked / total
```
This is called once per unique source in the candidate set, not once per candidate. Static fallback: if `_get_source_win_rate()` returns `None`, use `get_recommendation_weights()[source]`. [ASSUMED: win-rate replaces source-weight component if present; this depends on whether planner adds a source_weight term to the formula]

**Recommendation for planner:** Phase 2 formula has no source weight term. D-11's win-rate tracking is scaffolding for Phase 3. Phase 2 deliverable is writing `source` to `RecommendationLog`. Leave win-rate query for Phase 3. The cold-start threshold N=5 is still the right default.

---

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| numpy | 1.26.4 | Cosine similarity computation | Already imported in engine (line 12) |
| Django ORM | 5.1.3 | Migration, RecommendationLog queries | Already used throughout |
| spotipy | 2.23.0 | Spotify API client | Already used — no new calls needed for Phase 2 |

### No New Dependencies Required
Phase 2 needs no additional packages. numpy is already imported. scipy is installed but should NOT be imported (not in requirements.txt). [VERIFIED: requirements.txt]

---

## Architecture Patterns

### Taste Vector Build — Insertion Point

**Location:** `_update_profile_data()` lines 231-261, specifically AFTER the `self._update_top_artists(sp)` call at line 242.

**Insertion point:**
```python
def _update_profile_data(self):
    ...
    self._update_top_artists(sp)   # line 242 — existing
    self._update_saved_tracks(sp)  # line 243 — existing
    self._update_playlists(sp)     # line 244 — existing
    self._update_listening_patterns(sp)  # line 245 — existing
    self._build_taste_vector()     # NEW — add after line 245
    
    self.profile.save()            # line 248 — existing (catches taste vector too)
```

**`_build_taste_vector()` pattern:**
```python
def _build_taste_vector(self):
    """Build genre frequency vector from top_artists. Stored as raw counts."""
    top_artists = self.profile.data.get('base_data', {}).get('top_artists', [])
    taste_vector = {}
    for artist in top_artists:
        for genre in artist.get('genres', []):
            taste_vector[genre] = taste_vector.get(genre, 0) + 1
    self.profile.data['taste_vector'] = taste_vector
    logger.info(f"Built taste vector with {len(taste_vector)} genres from {len(top_artists)} artists")
```

### Scoring Function — Replacement Pattern

**Location:** Lines 717-748. Full method replacement.

**New `_score_recommendations()` skeleton:**
```python
def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
    """Score candidates: 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier"""
    taste_vector = self.profile.data.get('taste_vector', {})
    liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
    disliked_artists = self.profile.data.get('preferences', {}).get('disliked_artists', [])
    
    # Build artist->genres lookup from already-fetched top_artists
    artist_genre_lookup = {
        a['name']: a.get('genres', [])
        for a in self.profile.data.get('base_data', {}).get('top_artists', [])
    }
    
    for rec in recommendations:
        # genre_sim component
        candidate_genres = {g: 1.0 for g in artist_genre_lookup.get(rec.get('artist', ''), [])}
        genre_sim = self._cosine_similarity(candidate_genres, taste_vector)
        
        # novelty component
        popularity = rec.get('popularity', 50)
        novelty = 1.0 - (popularity / 100.0)
        
        # feedback_multiplier component
        artist = rec.get('artist', '')
        if artist in liked_artists:
            feedback_multiplier = 1.0
        elif artist in disliked_artists:
            feedback_multiplier = 0.0
        else:
            feedback_multiplier = 0.5
        
        rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier
    
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations
```

### Dead Code Deletion — `_update_weights_from_ai_feedback()`

**D-08:** Delete lines 898-934 (the full `_update_weights_from_ai_feedback` method).

**D-09:** In `add_ai_feedback()` (lines 867-896), remove the call to `self._update_weights_from_ai_feedback(interpretation)` at line 890. The surrounding code (storing ai_feedback_history, saving profile) stays intact.

**D-09 continued:** The three keys `tempo_weight`, `energy_weight`, `valence_weight` appear ONLY inside `_update_weights_from_ai_feedback()` — they are never in the default weights dict returned by `get_recommendation_weights()`. So no separate removal from defaults is needed. [VERIFIED: `get_recommendation_weights()` in models.py lines 138-146 — default dict has only: playlist_mining, artist_network, contextual, popularity, feedback]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity | Custom dot-product from scratch | numpy `np.dot` + `np.linalg.norm` | Already imported; 4 lines; handles edge cases |
| Genre vector normalization | Pre-normalize and store | Normalize at call time in `_cosine_similarity()` | D-03 explicitly requires raw counts stored; cosine normalizes dynamically |
| DB win-rate query | Complex ORM aggregate | `filter(source=s).count()` + `filter(source=s, liked=True).count()` | Two simple queries; no GROUP BY needed for single-source lookup |

---

## Common Pitfalls

### Pitfall 1: Empty Taste Vector on New Profile
**What goes wrong:** `_build_taste_vector()` runs, `top_artists` is `[]` (API failed or first-ever run), taste vector is `{}`. Then `_cosine_similarity({}, {})` returns 0.0 for all candidates. All genre_sim = 0.0. Score formula reduces to `0.3 * novelty + 0.3 * feedback_multiplier` — still functional, just ignoring genre component.
**Why it happens:** `_update_top_artists()` has a try/except that silently returns on failure.
**How to avoid:** The 0.0 return in `_cosine_similarity()` when either vector is empty IS the correct behavior. No extra guard needed — formula degrades gracefully.
**Warning signs:** All recommendations show identical `score` values (all `novelty`-driven). Log line will show "Built taste vector with 0 genres".

### Pitfall 2: `base_data` Key Not Initialized Before Access
**What goes wrong:** `self.profile.data.get('base_data', {}).get('top_artists', [])` — safe. But `self.profile.data['base_data']['top_artists']` (direct access) raises `KeyError` if profile was created before `_update_profile_data()` ran.
**Why it happens:** `_get_or_create_profile()` initializes `base_data` as `{}` (line 51), not `{'top_artists': []}`.
**How to avoid:** Always use `.get()` with defaults in `_build_taste_vector()` and the scoring function. The pattern is already used correctly in `_get_related_artist_recommendations()` (line 503).

### Pitfall 3: `preferences` Key Access Without Guard
**What goes wrong:** `self.profile.data['preferences'].get('liked_artists', [])` raises `KeyError` if the profile was created with the old initialization that omitted `preferences`.
**Why it happens:** The current `_score_recommendations()` at line 720 already has this bug — `self.profile.data['preferences']` without `.get()`.
**How to avoid:** Use `self.profile.data.get('preferences', {}).get('liked_artists', [])` — the same pattern used in `remove_feedback()` (line 854).

### Pitfall 4: `popularity` Division — Track Popularity vs Artist Popularity
**What goes wrong:** Recommendation dicts carry `popularity` for the TRACK (0-100 from Spotify's track object). The novelty formula `1 - (popularity / 100)` is correct for track popularity. But `_update_top_artists()` also stores `artist['popularity']` in `base_data`. Don't confuse them.
**How to avoid:** Novelty reads `rec.get('popularity', 50)` from the recommendation dict — this is track popularity. [VERIFIED: all four strategy methods set `'popularity': track.get('popularity', 0)` in the rec dict]

### Pitfall 5: Score Range — Post-Randomization in `get_recommendations()`
**What goes wrong:** After `_score_recommendations()` returns, `get_recommendations()` adds `random.uniform(-0.1, 0.1)` to each score (lines 152-153) and re-sorts. This is fine — Phase 2 just needs to ensure the pre-randomization score is in a reasonable range.
**Why it matters:** The new formula produces scores in [0.0, 1.0] (all three components are in [0,1]). The randomization adds ±0.1. No change needed — but tests that check exact score values should account for this downstream noise.

---

## Migration Execution

**File to create:** Auto-generated. Run:
```bash
cd /path/to/songscope/backend
python manage.py makemigrations core --name recommendationlog_source
python manage.py migrate
```

**Dependency chain in generated file will be:**
```python
dependencies = [
    ("core", "0005_dailygem_image_url_dailygem_preview_url"),
]
```

**Test migration is clean:**
```bash
python manage.py migrate --check  # should exit 0 after running migrate
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `python -m pytest`) |
| Config file | `backend/pytest.ini` (established in Phase 1) |
| Quick run command | `cd backend && python -m pytest tests/test_recommendation.py tests/test_feedback.py -v` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase 2 Requirements -> Test Map

| Req | Behavior | Test Type | Automated Command | File |
|-----|----------|-----------|-------------------|------|
| D-02/D-03 | `_build_taste_vector()` counts genres flat from top_artists | unit | `pytest tests/test_scoring.py::TestTasteVector -x` | Wave 0 gap |
| D-03 | Taste vector stored at `profile.data['taste_vector']` | unit | same | Wave 0 gap |
| D-05 | `_cosine_similarity()` returns 1.0 for identical vectors | unit | `pytest tests/test_scoring.py::TestCosineSimilarity -x` | Wave 0 gap |
| D-05 | `_cosine_similarity()` returns 0.0 when either vector empty | unit | same | Wave 0 gap |
| D-06 | novelty = 1 - (popularity/100) | unit | `pytest tests/test_scoring.py::TestScoreFormula -x` | Wave 0 gap |
| formula | Score formula sums to correct value given known inputs | unit | same | Wave 0 gap |
| D-07 | liked artist → feedback_multiplier = 1.0 | unit | same | Wave 0 gap |
| D-07 | disliked artist → feedback_multiplier = 0.0 | unit | same | Wave 0 gap |
| D-08 | `_update_weights_from_ai_feedback` does not exist on engine | unit | `pytest tests/test_scoring.py::TestDeadCodeRemoval -x` | Wave 0 gap |
| D-10 | `RecommendationLog.source` field exists and accepts valid choices | unit (DB) | `pytest tests/test_scoring.py::TestRecommendationLogSource -x` | Wave 0 gap |
| D-10 | `log_recommendation()` writes source value | unit (DB) | same | Wave 0 gap |

### Sampling Rate
- Per task commit: `cd backend && python -m pytest tests/test_scoring.py -x -q`
- Per wave merge: `cd backend && python -m pytest tests/ -v`
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_scoring.py` — new file covering D-02/D-03/D-05/D-06/D-07/D-08/D-10
- [ ] No new conftest.py needed — existing `tests/conftest.py` covers Django setup

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | feedback_multiplier values: liked=1.0, neutral=0.5, disliked=0.0 | Q3 / Scoring Pattern | Score range shifts; planner should confirm or adjust |
| A2 | scipy should not be added to requirements.txt | Q2 | If scipy is already tracked elsewhere, using it is fine and saves 4 lines |
| A3 | `_calculate_feature_preferences()` dead code should be deferred, not deleted in Phase 2 | Q6 | If planner includes it, must also update track_discovery_engine.py and views.py callers |
| A4 | Win-rate query is Phase 3 concern, not Phase 2 | Q8 | If planner treats D-11 as Phase 2 scoring component, scoring formula needs a 4th term |
| A5 | No other call sites for `log_recommendation()` beyond views.py:336 | Q5 | Grep confirmed; test files use `objects.create()` directly |

---

## Open Questions

1. **feedback_multiplier neutral value**
   - What we know: liked=bump, disliked=penalty. CONTEXT D-07 says "positive bump; negative penalty" but gives no specific values.
   - What's unclear: Neutral midpoint value and scale. Using 0.5 neutral means an unknown artist contributes `0.3 * 0.5 = 0.15` to the score regardless of genre/novelty.
   - Recommendation: Use 1.0 / 0.5 / 0.0. Planner should confirm.

2. **Phase 2 scope of D-11**
   - What we know: D-11 describes win-rate replacing static weights with a cold-start fallback.
   - What's unclear: Whether win-rate querying should be implemented in Phase 2 scoring or deferred to Phase 3 when Thompson Sampling is introduced.
   - Recommendation: Defer to Phase 3. Phase 2 only writes `source` to `RecommendationLog` so Phase 3 has the data.

---

## Sources

### Primary (HIGH confidence — verified by reading actual source files)
- `backend/apps/recommendations/hybrid_recommendation_engine.py` — `_score_recommendations()` lines 717-748, `_update_top_artists()` lines 263-281, `add_ai_feedback()` lines 867-896, `_update_weights_from_ai_feedback()` lines 898-934, numpy import line 12
- `backend/apps/core/models.py` — `Track.genres` field (line 167), `RecommendationLog.log_recommendation()` (lines 242-248), `UserProfile.get_recommendation_weights()` (lines 138-146)
- `backend/apps/core/views.py` — `log_recommendation` call site (line 336), Track genre population (lines 554-562)
- `backend/apps/core/migrations/` — 0003, 0004, 0005 migration files (migration pattern and dependency chain)
- `backend/apps/recommendations/personalization_engine.py` — `_calculate_feature_preferences()` (lines 84-92), dead code confirmed
- `backend/tests/` — conftest.py, test_recommendation.py, test_feedback.py, test_personalization.py (test patterns)
- `backend/requirements.txt` — confirmed numpy/scipy not listed as project dependencies

### Tertiary (ASSUMED — not verified in this session)
- feedback_multiplier specific values (1.0/0.5/0.0) — reasonable defaults, not specified in CONTEXT.md
- Win-rate as Phase 3 concern — interpretation of D-11 scope

---

## Metadata

**Confidence breakdown:**
- Track.genres availability: HIGH — verified by reading all four strategy methods and views.py
- Cosine similarity approach: HIGH — numpy already imported; scipy not in requirements.txt
- Migration pattern: HIGH — verified 5 existing migrations
- log_recommendation call sites: HIGH — grep confirmed single call site
- Dead code confirmation: HIGH — _calculate_feature_preferences verified stub; _update_weights_from_ai_feedback lines 898-934 verified
- Test patterns: HIGH — read all four test files in Phase 1 test suite
- Scoring insertion point: HIGH — _score_recommendations lines 717-748 fully read and transcribed

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable codebase, no fast-moving deps)

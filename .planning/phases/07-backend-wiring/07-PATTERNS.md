# Phase 7: Backend Wiring - Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 5 (3 modified, 2 extended test files)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/apps/core/views.py` (`get_daily_gem` fresh branch) | view / CRUD write | request-response | `backend/apps/core/views.py` `submit_feedback` was_liked block (lines 687–694) | exact — same model, same ORM write via `get_or_create` |
| `backend/apps/core/views.py` (`get_daily_gem` cached branches) | view / CRUD read | request-response | `backend/apps/core/views.py` `get_daily_gem` cached branch (line 1044–1061) | exact — same gem object read pattern |
| `backend/apps/core/views.py` (`_build_gem_explanation` helper) | utility / pure function | transform | `backend/apps/core/views.py` `_jaccard_distance` helper (imported at test line 24) | role-match — module-level private helper in same file |
| `backend/apps/core/views.py` (`add_track_to_liked` was_saved wiring) | view / CRUD write | request-response | `backend/apps/core/views.py` `submit_feedback` was_liked non-fatal block (lines 631–637) | exact — same non-fatal try/except + ORM update pattern |
| `backend/apps/core/views.py` (`get_recommendation_metrics` compound_hit_rate) | view / aggregate query | request-response | `backend/apps/core/views.py` `gem_acceptance_rate` computation (lines 421–424) | exact — same gem_list sum() idiom |
| `backend/tests/test_feedback.py` (extend `TestWasSavedWiring`) | test / ORM round-trip | CRUD | `backend/tests/test_feedback.py` `TestDailyGemWasLikedSync` (lines 69–199) | exact — same ORM + mock Spotify client test class structure |
| `backend/tests/test_views_gem_feedback.py` (extend `TestGetDailyGemCached` + new `TestBuildGemExplanation` + new `TestGetDailyGemFreshScores`) | test / view-level | request-response | `backend/tests/test_views_gem_feedback.py` `TestGetDailyGemCached` (lines 39–76) and `TestGetDailyGemRace` (lines 103–145) | exact |
| `backend/tests/test_metrics.py` (extend `TestMetricsEndpoint`) | test / endpoint | request-response | `backend/tests/test_metrics.py` `TestMetricsEndpoint` (lines 60–166) | exact |

---

## Pattern Assignments

### `views.py` — `get_daily_gem` fresh branch: expand `get_or_create` defaults (SCHEMA-02, SCHEMA-03, EXPLAIN-02)

**Analog:** `backend/apps/core/views.py` lines 1094–1105 (existing `get_or_create`)

**Current state** (lines 1094–1105):
```python
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

**Available data in scope at this line** (lines 1075–1093):
```python
engine = HybridRecommendationEngine(request.user)
candidates = engine.get_recommendations(limit=10, force_fresh=force_new)
# ...
gem_data = candidates[0]  # line 1082 — has score_breakdown + score keys
```

**Engine profile access pattern** — `engine.profile.data` is the `UserProfile.data` JSONField; the taste vector lives at `engine.profile.data.get('taste_vector', {})`.

**Target state** — expand `defaults` to include 4 new fields, calling `_build_gem_explanation` inline:
```python
breakdown = gem_data.get('score_breakdown', {})
taste_snapshot = engine.profile.data.get('taste_vector', {})

gem, created = DailyGem.objects.get_or_create(
    user=request.user,
    date=today,
    defaults={
        'track': track_obj,
        'explanation': _build_gem_explanation(
            breakdown,
            gem_data.get('name', ''),
            gem_data.get('artist', ''),
            breakdown.get('source', ''),
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

**Also fix: fresh-branch final `JsonResponse` explanation field** (line 1136 — currently `'explanation': ''`):
```python
# Before (line 1136):
'explanation': '',

# After:
'explanation': gem.explanation,
```
The gem object is in scope after `get_or_create` (line 1095); read the persisted field for consistency.

---

### `views.py` — `get_daily_gem` cached branches: fix `score_breakdown: {}` (SCHEMA-04)

**Analog:** Same function — gem object is already fetched from DB at both sites.

**Cached branch (line 1060):**
```python
# Before:
'score_breakdown': {},

# After:
'score_breakdown': gem.score_breakdown,
```
The `gem` object is fetched at line 1045 (`DailyGem.objects.get(user=request.user, date=today)`). `gem.score_breakdown` is a direct field read — no extra DB call.

**Race-condition branch (line 1123):**
```python
# Before:
'score_breakdown': {},

# After:
'score_breakdown': gem.score_breakdown,
```
The `gem` object is in scope from `get_or_create` (line 1095). Same pattern.

Note: Both branches already read `gem.explanation` correctly (lines 1057, 1120). Only `score_breakdown` is hardcoded as `{}`.

---

### `views.py` — `_build_gem_explanation` pure helper function (EXPLAIN-01)

**Analog placement:** Module-level private helper in `views.py`. The existing `_jaccard_distance` function (imported by tests at `from apps.core.views import _jaccard_distance`) confirms this is the established pattern for module-level private helpers in this file.

**Function must be placed before `get_daily_gem`** (line 1026) so it is in scope when called inside `defaults`.

**Signature and logic (from D-01 through D-06):**
```python
def _build_gem_explanation(breakdown: dict, track_name: str, artist_name: str, source: str) -> str:
    """
    Pure function: deterministic explanation sentence from dominant score component.
    No external calls. Zero latency risk. Exception-safe — any failure returns fallback.
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

**Score breakdown structure from engine** (`hybrid_recommendation_engine.py` lines 875–880):
```python
rec['score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'source': rec.get('source', ''),
}
rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier
```

No genre name is available in the breakdown dict — only numeric scores. Use `"your listening taste"` as the label (already encoded in the genre_sim branch above).

---

### `views.py` — `add_track_to_liked` was_saved wiring (D-07 through D-09)

**Analog:** `backend/apps/core/views.py` `submit_feedback` was_liked non-fatal block (lines 631–637)

**Existing was_liked pattern** (lines 631–637):
```python
gem = DailyGem.objects.filter(
    user=request.user, date=timezone.localdate(), track=track
).first()
if gem:
    gem.was_liked = None
    gem.save(update_fields=['was_liked'])
```

**Key distinction:** was_saved uses `.filter().update()` (not `.first()` + `.save()`), because the lookup is by `track__spotify_id` FK traversal — no object instantiation needed, and `.update()` silently returns 0 when no rows match.

**Existing `add_track_to_liked` view** (lines 829–854):
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_track_to_liked(request):
    try:
        track_id = request.data.get("track_id")
        if not track_id:
            return JsonResponse({'error': 'track_id is required'}, status=400)

        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)

        sp = get_spotipy_client(spotify_token.access_token)
        sp.current_user_saved_tracks_add([track_id])   # <-- insert after this line

        return JsonResponse({'message': "all good"})
    except SpotifyException as e:
        ...
```

**Target insertion** — after line 843 (`sp.current_user_saved_tracks_add([track_id])`), before the `return`:
```python
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

return JsonResponse({'message': "all good"})
```

`timezone` is already imported at line 12. `DailyGem` is already imported at line 21. No new imports needed.

---

### `views.py` — `get_recommendation_metrics` compound_hit_rate (METRIC-02)

**Analog:** `backend/apps/core/views.py` `gem_acceptance_rate` computation (lines 421–424)

**Existing gem_acceptance_rate pattern** (lines 414–424):
```python
gems = DailyGem.objects.filter(user=user).order_by('date')
gem_list = list(gems.values('was_liked', 'track_popularity', 'date', 'track_id'))
gem_total = len(gem_list)

if gem_total == 0:
    return JsonResponse({'message': 'No gems yet'})

gem_liked = sum(1 for g in gem_list if g['was_liked'] is True)
gem_disliked = sum(1 for g in gem_list if g['was_liked'] is False)
gem_acceptance_rate = gem_liked / gem_total
```

**Two-part change required:**

1. Add `'was_saved'` to the `.values()` call at line 415 (or `KeyError` at runtime):
```python
# Before (line 415):
gem_list = list(gems.values('was_liked', 'track_popularity', 'date', 'track_id'))

# After:
gem_list = list(gems.values('was_liked', 'was_saved', 'track_popularity', 'date', 'track_id'))
```

2. Add compound_hit_rate computation immediately after `gem_acceptance_rate` (after line 424):
```python
# After gem_acceptance_rate = gem_liked / gem_total:
compound_hits = sum(
    1 for g in gem_list
    if g['was_liked'] is True or g['was_saved'] is True
)
compound_hit_rate = compound_hits / gem_total if gem_total > 0 else 0.0
```

3. Add `'compound_hit_rate': compound_hit_rate` to the `return JsonResponse({...})` dict at line 480–493. The key must always be present (D-13).

---

### `backend/tests/test_feedback.py` — new `TestWasSavedWiring` class

**Analog:** `backend/tests/test_feedback.py` `TestDailyGemWasLikedSync` (lines 69–199)

**setUp pattern** (lines 80–101):
```python
def setUp(self):
    from datetime import date
    from apps.core.models import DailyGem
    self.user = User.objects.create_user('gemuser', password='pw')
    self.track = Track.objects.create(
        spotify_id='B' * 22,
        name='Gem Track',
        artist='Artist',
        album='Album',
    )
    self.gem = DailyGem.objects.create(
        user=self.user, date=date.today(), track=self.track,
    )
    self.token = SpotifyToken.objects.create(
        user=self.user,
        access_token='fake_access_token',
        refresh_token='fake_refresh_token',
        expires_at=timezone.now() + timedelta(days=3650),
    )
    self.client.force_login(self.user)
```

**Mock Spotify client pattern** (lines 137–154):
```python
@patch('apps.core.views.HybridRecommendationEngine')
@patch('apps.recommendations.personalization_engine.PersonalizationEngine')
@patch('apps.core.views.get_spotipy_client')
def test_view_sets_was_liked_true_on_like(self, mock_sp_client, mock_pe, mock_hre):
    mock_sp_client.return_value = MagicMock()
    mock_pe.return_value = MagicMock()
    mock_hre.return_value = MagicMock()
    # ...
    self.gem.refresh_from_db()
    self.assertTrue(self.gem.was_liked)
```

For `TestWasSavedWiring`: mock only `apps.core.views.get_spotipy_client` (no personalization engine involved in `add_track_to_liked`). The `mock_sp_client.return_value.current_user_saved_tracks_add` must be a MagicMock that does not raise.

**ORM round-trip assertion pattern** (lines 103–108):
```python
def test_was_liked_set_true_on_like(self):
    self.gem.was_liked = True
    self.gem.save(update_fields=['was_liked'])
    self.gem.refresh_from_db()
    self.assertTrue(self.gem.was_liked)
```

---

### `backend/tests/test_views_gem_feedback.py` — extend + new classes

**Analog:** `backend/tests/test_views_gem_feedback.py` `TestGetDailyGemCached` (lines 39–76) and `TestGetDailyGemRace` (lines 103–145)

**Fixture / setUp pattern** (lines 40–57):
```python
def setUp(self):
    self.user = _make_user_with_token("cached_gem_user")
    self.client.force_login(self.user)
    self.track = Track.objects.create(
        spotify_id="A" * 22,
        name="Cached Track",
        artist="Artist",
        album="Album",
    )
    DailyGem.objects.create(
        user=self.user,
        date=timezone.localdate(),
        track=self.track,
        explanation="cached gem explanation",
        image_url="http://img.example.com/art.jpg",
        preview_url="http://preview.example.com/30s.mp3",
        track_popularity=42,
    )
```

**Mock engine pattern for fresh branch tests** (lines 114–129):
```python
@patch("apps.core.views.HybridRecommendationEngine")
def test_race_returns_existing_gem(self, MockEngine):
    instance = MockEngine.return_value
    instance.get_recommendations.return_value = [
        {
            "id": "B" * 22,
            "name": "Race Track",
            "artist": "Artist",
            "album": "Album",
            "popularity": 30,
            "image_url": None,
            "preview_url": None,
            "source": "test",
            "score": 0.9,
        }
    ]
```

For `TestGetDailyGemFreshScores`, the mock candidate dict must also include `score_breakdown` and the `instance.profile.data` must return a dict with `taste_vector`. Use `instance.profile.data.get.return_value = {}` or set `instance.profile.data = {'taste_vector': {'indie rock': 5}}`.

---

### `backend/tests/test_metrics.py` — extend `TestMetricsEndpoint`

**Analog:** `backend/tests/test_metrics.py` `TestMetricsEndpoint.test_response_includes_all_phase4_fields` (lines 138–166)

**Required fields assertion pattern** (lines 150–166):
```python
required_fields = [
    'total_recommended', 'avg_popularity', 'novel_track_rate',
    'hidden_gem_rate', 'gem_total', 'gem_liked', 'gem_disliked',
    'gem_acceptance_rate', 'top_genres', 'top_genres_pct',
    'improvement_story', 'diversity_score',
]
for field in required_fields:
    self.assertIn(field, data, msg=f"Missing field: {field}")
```

**`_make_gem` helper** (lines 45–53) — use as-is for new tests; add `was_saved` kwarg:
```python
def _make_gem(user, track, date, was_liked=None, was_saved=None, track_popularity=50):
    return DailyGem.objects.create(
        user=user, track=track, date=date,
        was_liked=was_liked, was_saved=was_saved,
        track_popularity=track_popularity,
    )
```

**Metric formula test pattern** — follow `test_hidden_gem_rate_uses_track_popularity_lt_40` (lines 111–135): create N gems with known `was_liked`/`was_saved` values, call endpoint, assert `data['compound_hit_rate']` equals expected float.

---

## Shared Patterns

### Authentication / Permissions
**Source:** `backend/apps/core/views.py` lines 829–831, 1024–1025
**Apply to:** All modified views
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_track_to_liked(request):
```
All 3 affected views (`add_track_to_liked`, `get_daily_gem`, `get_recommendation_metrics`) already carry `@api_view` + `@permission_classes([IsAuthenticated])`. No changes needed.

### Non-fatal try/except wrapper
**Source:** `backend/apps/core/views.py` lines 631–637 (was_liked non-fatal) and lines 698–700 (outer exception handler)
**Apply to:** `was_saved` block in `add_track_to_liked`
```python
try:
    # ORM update — returns 0 silently if no rows match
    DailyGem.objects.filter(...).update(was_saved=True)
except Exception:
    pass  # Silent no-op — caller already succeeded
```
The outer view try/except (lines 847–854) handles `SpotifyException` and generic `Exception` separately. The inner non-fatal block uses a bare `except Exception: pass` to match the existing was_liked pattern.

### ORM queryset sum() for metrics
**Source:** `backend/apps/core/views.py` lines 421–424
**Apply to:** `compound_hit_rate` computation
```python
gem_liked = sum(1 for g in gem_list if g['was_liked'] is True)
gem_acceptance_rate = gem_liked / gem_total
```
Use `is True` (identity check) not `== True` to distinguish `True` from `None`. Apply same idiom for `compound_hit_rate`.

### `timezone.localdate()` for date
**Source:** `backend/apps/core/views.py` lines 1041, 632
**Apply to:** `was_saved` filter in `add_track_to_liked`
```python
today = timezone.localdate()
```
`timezone` is imported at line 12. Use `timezone.localdate()` everywhere — not `date.today()` — to match the Django-aware date convention used throughout the file.

### test `force_login` + JSON response assertion
**Source:** `backend/tests/test_views_gem_feedback.py` lines 59–70, `backend/tests/test_metrics.py` lines 83–89
**Apply to:** All new test methods
```python
self.client.force_login(self.user)
response = self.client.get(self.ENDPOINT)
self.assertEqual(response.status_code, 200)
data = response.json()  # or json.loads(response.content)
self.assertIn('compound_hit_rate', data)
```

---

## No Analog Found

All files have direct analogs in the existing codebase. No entries.

---

## Metadata

**Analog search scope:** `backend/apps/core/views.py`, `backend/apps/core/models.py`, `backend/tests/test_feedback.py`, `backend/tests/test_views_gem_feedback.py`, `backend/tests/test_metrics.py`
**Files scanned:** 5
**Pattern extraction date:** 2026-05-14

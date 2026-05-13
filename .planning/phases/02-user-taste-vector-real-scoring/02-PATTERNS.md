# Phase 2: User Taste Vector & Real Scoring - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 5 new/modified files
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/apps/recommendations/hybrid_recommendation_engine.py` | service | transform | `hybrid_recommendation_engine.py` itself (existing methods in same file) | exact — same class, same data shapes |
| `backend/apps/core/models.py` | model | CRUD | `backend/apps/core/models.py` existing `RecommendationLog` class | exact — AddField to existing model |
| `backend/apps/core/migrations/0006_recommendationlog_source.py` | migration | batch | `backend/apps/core/migrations/0005_dailygem_image_url_dailygem_preview_url.py` | exact — same AddField pattern |
| `backend/apps/core/views.py` | controller | request-response | `backend/apps/core/views.py` lines 327-336 (the `log_recommendation` call site itself) | exact — one-line change at same site |
| `backend/tests/test_scoring.py` | test | transform | `backend/tests/test_recommendation.py` | exact — same unittest.TestCase + __new__ bypass pattern |

---

## Pattern Assignments

### `hybrid_recommendation_engine.py` — `_score_recommendations()` replacement (lines 717-748)

**Analog:** Same file — current `_score_recommendations()` implementation.

**Current implementation to replace — full verbatim** (lines 717-748):
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

**Function signature to preserve:**
- Input: `(self, recommendations: List[Dict]) -> List[Dict]`
- Each dict has keys: `id`, `name`, `artist`, `album`, `preview_url`, `image_url`, `source`, `score`, `popularity`
- Mutates `rec['score']` in-place; returns list sorted descending by `score`
- Single call site at line 144: `scored_recommendations = self._score_recommendations(unique_recommendations)`

**Replacement skeleton to drop in:**
```python
def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
    """Score candidates: 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier"""
    taste_vector = self.profile.data.get('taste_vector', {})
    liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
    disliked_artists = self.profile.data.get('preferences', {}).get('disliked_artists', [])

    # Build artist->genres lookup from already-fetched top_artists (zero API calls)
    artist_genre_lookup = {
        a['name']: a.get('genres', [])
        for a in self.profile.data.get('base_data', {}).get('top_artists', [])
    }

    for rec in recommendations:
        # genre_sim component
        candidate_genres = {g: 1.0 for g in artist_genre_lookup.get(rec.get('artist', ''), [])}
        genre_sim = self._cosine_similarity(candidate_genres, taste_vector)

        # novelty component (track popularity, not artist popularity)
        novelty = 1.0 - (rec.get('popularity', 50) / 100.0)

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

---

### `hybrid_recommendation_engine.py` — `_cosine_similarity()` new helper method

**Analog:** numpy is already imported at line 12 — `import numpy as np`. No new imports needed.

**Pattern (add as a private method before `_score_recommendations`):**
```python
def _cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
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

---

### `hybrid_recommendation_engine.py` — `_build_taste_vector()` insertion point

**Analog:** `_update_top_artists()` (lines 263-281) — same pattern: private method, reads from `self.profile.data`, mutates `self.profile.data[key]`, logs result.

**`_update_top_artists()` pattern to mirror** (lines 263-281):
```python
def _update_top_artists(self, sp):
    """Update user's top artists"""
    try:
        if not self._check_rate_limit():
            return

        top_artists = sp.current_user_top_artists(limit=20)
        self.profile.data['base_data']['top_artists'] = [
            {
                'id': artist['id'],
                'name': artist['name'],
                'genres': artist['genres'],
                'popularity': artist['popularity']
            }
            for artist in top_artists['items']
        ]
    except Exception as e:
        logger.error(f"Error updating top artists: {str(e)}")
        self._add_error('top_artists', 'api_failure', str(e))
```

**Insertion point in `_update_profile_data()`:** Add call AFTER `self._update_top_artists(sp)` at line 242 and BEFORE `self.profile.save()` at line 248:
```python
self._update_top_artists(sp)          # line 242 — existing
self._update_saved_tracks(sp)         # line 243 — existing
self._update_playlists(sp)            # line 244 — existing
self._update_listening_patterns(sp)   # line 245 — existing
self._build_taste_vector()            # NEW — add here, before save
self.profile.save()                   # line 248 — existing
```

**`_build_taste_vector()` new method:**
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

---

### `hybrid_recommendation_engine.py` — `_update_weights_from_ai_feedback()` deletion (lines 898-934)

**What to delete:** Lines 898-934 (the entire `_update_weights_from_ai_feedback` method body and `def` line).

**What to remove from `add_ai_feedback()` (lines 867-896):** The single call to `self._update_weights_from_ai_feedback(interpretation)` at approximately line 890. The rest of `add_ai_feedback()` (storing AI feedback history, saving profile) stays intact.

**Verification:** The three keys `tempo_weight`, `energy_weight`, `valence_weight` exist ONLY inside `_update_weights_from_ai_feedback()`. They are NOT in the default dict returned by `get_recommendation_weights()` in models.py (lines 138-146 return only: `playlist_mining`, `artist_network`, `contextual`, `popularity`, `feedback`). No model migration needed for this deletion.

---

### `backend/apps/core/models.py` — `RecommendationLog.source` field addition

**Analog:** Existing `RecommendationLog` model in the same file. `was_novel = models.BooleanField(null=True)` is the field immediately before where `source` should be added.

**Current `log_recommendation()` signature** (lines 242-248):
```python
@classmethod
def log_recommendation(cls, user, track):
    """Log a track recommendation"""
    try:
        cls.objects.create(user=user, track=track)
    except Exception as e:
        logger.error(f"Error logging recommendation: {str(e)}")
```

**New field to add to `RecommendationLog` class** (after `was_novel`):
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

**Updated `log_recommendation()` signature** (backward-compatible, default preserves existing callers):
```python
@classmethod
def log_recommendation(cls, user, track, source=''):
    """Log a track recommendation"""
    try:
        cls.objects.create(user=user, track=track, source=source)
    except Exception as e:
        logger.error(f"Error logging recommendation: {str(e)}")
```

---

### `backend/apps/core/migrations/0006_recommendationlog_source.py`

**Analog:** `backend/apps/core/migrations/0005_dailygem_image_url_dailygem_preview_url.py` — same `AddField` operation pattern.

**Migration naming convention verified from existing files:**
- `0001_initial.py`
- `0002_userprofile_data.py`
- `0003_track_genres_userfeedback_feedback_type_and_more.py`
- `0004_recommendationlog_track_popularity_and_more.py`
- `0005_dailygem_image_url_dailygem_preview_url.py`
- Next: `0006_recommendationlog_source.py` (auto-generated name)

**Generation command (do not hand-write):**
```bash
cd backend
python manage.py makemigrations core --name recommendationlog_source
python manage.py migrate
```

**Expected generated content pattern** (from verified 0004 and 0005):
```python
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_dailygem_image_url_dailygem_preview_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendationlog",
            name="source",
            field=models.CharField(
                blank=True,
                choices=[
                    ('playlist_mining', 'Playlist Mining'),
                    ('artist_network', 'Artist Network'),
                    ('genre_search', 'Genre Search'),
                    ('related_artists', 'Related Artists'),
                    ('contextual', 'Contextual'),
                ],
                default='',
                max_length=50,
            ),
        ),
    ]
```

---

### `backend/apps/core/views.py` — `log_recommendation()` call site (line 336)

**Analog:** Same file, existing call site at lines 327-336.

**Current call site** (lines 327-336):
```python
# Log recommendations
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

**Updated call site** (one-line change — add `source=` kwarg):
```python
RecommendationLog.log_recommendation(request.user, track_obj, source=track.get('source', ''))
```

The `processed_track` dict at line 316 already sets `'source': track.get('source', 'unknown')` — the value is present. No structural change to the loop.

---

### `backend/tests/test_scoring.py` — new test file

**Analog:** `backend/tests/test_recommendation.py` — same file structure, same import patterns, same two-base-class pattern.

**Imports pattern** (copy from `test_recommendation.py` lines 1-12):
```python
"""
Unit tests for Phase 2 scoring: taste vector build, cosine similarity, score formula,
dead code removal, RecommendationLog.source field.
"""
import unittest
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import RecommendationLog, Track, UserProfile
```

**conftest.py pattern** (already exists — no new conftest needed):
```python
# backend/tests/conftest.py — existing, Phase 2 tests inherit automatically
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()
```

**Pattern A — DB-backed test** (copy from `test_recommendation.py:TestPersistentExclusionSet`):
```python
class TestRecommendationLogSource(TestCase):
    """D-10: RecommendationLog.source field stores source value."""

    def setUp(self):
        self.user = User.objects.create_user('srcuser', password='pw')
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'data': {'base_data': {'top_artists': []}, 'preferences': {}}},
        )
        self.track = Track.objects.create(
            spotify_id='src_track_1',
            name='Source Track',
            artist='Artist',
            album='Album',
        )

    def test_log_recommendation_writes_source(self):
        RecommendationLog.log_recommendation(self.user, self.track, source='playlist_mining')
        log = RecommendationLog.objects.get(user=self.user, track=self.track)
        self.assertEqual(log.source, 'playlist_mining')

    def test_log_recommendation_default_source_is_empty(self):
        RecommendationLog.log_recommendation(self.user, self.track)
        log = RecommendationLog.objects.get(user=self.user, track=self.track)
        self.assertEqual(log.source, '')
```

**Pattern B — mock-based test without DB** (copy from `test_recommendation.py:TestRelatedArtistStrategy`):
```python
class TestScoreFormula(unittest.TestCase):
    """D-05/D-06/D-07: score = 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier"""

    def _make_engine(self, taste_vector, liked_artists=None, disliked_artists=None, top_artists=None):
        """Bypass __init__ — pattern from test_recommendation.py:144."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {
            'taste_vector': taste_vector,
            'base_data': {'top_artists': top_artists or []},
            'preferences': {
                'liked_artists': liked_artists or [],
                'disliked_artists': disliked_artists or [],
            },
        }
        return engine

    def test_score_liked_artist_boosts_feedback_multiplier(self):
        engine = self._make_engine(
            taste_vector={'indie rock': 5},
            liked_artists=['Great Artist'],
            top_artists=[{'name': 'Great Artist', 'genres': ['indie rock']}],
        )
        recs = [{'id': 'x', 'name': 'T', 'artist': 'Great Artist',
                 'album': 'A', 'preview_url': None, 'image_url': None,
                 'source': 'artist_network', 'score': 0.0, 'popularity': 50}]
        result = engine._score_recommendations(recs)
        # feedback_multiplier=1.0, novelty=0.5, genre_sim=1.0 (exact match)
        # score = 0.4*1.0 + 0.3*0.5 + 0.3*1.0 = 0.4 + 0.15 + 0.3 = 0.85
        self.assertAlmostEqual(result[0]['score'], 0.85, places=4)

    def test_score_disliked_artist_zeroes_feedback_multiplier(self):
        engine = self._make_engine(
            taste_vector={},
            disliked_artists=['Bad Artist'],
        )
        recs = [{'id': 'x', 'name': 'T', 'artist': 'Bad Artist',
                 'album': 'A', 'preview_url': None, 'image_url': None,
                 'source': 'playlist_mining', 'score': 0.0, 'popularity': 0}]
        result = engine._score_recommendations(recs)
        # genre_sim=0.0 (no taste vector), novelty=1.0 (popularity=0), feedback=0.0
        # score = 0.4*0.0 + 0.3*1.0 + 0.3*0.0 = 0.30
        self.assertAlmostEqual(result[0]['score'], 0.30, places=4)
```

**Test runner commands:**
```bash
# Per-task quick run
cd backend && python -m pytest tests/test_scoring.py -x -q

# Per-wave full suite
cd backend && python -m pytest tests/ -v
```

---

## Shared Patterns

### Profile Data Access Pattern
**Source:** `hybrid_recommendation_engine.py` — `_get_related_artist_recommendations()` line 503 and `remove_feedback()` line 854.
**Apply to:** All new methods in `hybrid_recommendation_engine.py`
**Rule:** Always use `.get()` with defaults, never direct key access. `self.profile.data['preferences']` raises `KeyError` on new profiles.
```python
# Correct — use .get() chained
taste_vector = self.profile.data.get('taste_vector', {})
liked = self.profile.data.get('preferences', {}).get('liked_artists', [])
top_artists = self.profile.data.get('base_data', {}).get('top_artists', [])

# Wrong — direct access crashes on new profiles
liked = self.profile.data['preferences'].get('liked_artists', [])
```

### Error Handling Pattern
**Source:** `hybrid_recommendation_engine.py` — all `_update_*()` methods (lines 263-370).
**Apply to:** `_build_taste_vector()` if any error risk exists (though the method is pure computation with no API calls, a try/except is optional but consistent).
```python
try:
    # ... operation
except Exception as e:
    logger.error(f"Error in <method_name>: {str(e)}")
    # self._add_error('endpoint_name', 'error_type', str(e))  # only for API-backed methods
```

### Django Migration Pattern
**Source:** `backend/apps/core/migrations/0004_recommendationlog_track_popularity_and_more.py` (verified AddField pattern).
**Apply to:** `0006_recommendationlog_source.py`
**Rule:** Do NOT hand-write migrations. Run `python manage.py makemigrations core --name recommendationlog_source` and commit the generated file unmodified.

### Test `__new__` Bypass Pattern
**Source:** `backend/tests/test_recommendation.py` line 144.
**Apply to:** All `unittest.TestCase` tests for scoring logic (no DB needed).
```python
from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
engine.user = Mock(id=99)
engine.profile = Mock()
engine.profile.data = {
    'taste_vector': {...},
    'base_data': {'top_artists': [...]},
    'preferences': {'liked_artists': [], 'disliked_artists': []},
}
```

---

## No Analog Found

All files have close analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `backend/apps/recommendations/`, `backend/apps/core/`, `backend/tests/`
**Key files read:** `hybrid_recommendation_engine.py` (lines 717-748, 263-281, 1-15), `models.py` (lines 138-248), `views.py` (lines 310-343, 530-562), `conftest.py` (full), `test_recommendation.py` (full), `test_personalization.py` (full), migrations 0003/0004/0005
**Pattern extraction date:** 2026-05-07
**Source data:** Verified against actual source file reads in prior researcher session (cwd confirmed as `/Users/antonilueddeke/Desktop/Projects/songscope`)

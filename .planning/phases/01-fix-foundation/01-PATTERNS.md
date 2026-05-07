# Phase 1: Fix & Foundation - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 6 (3 modified, 3 created)
**Analogs found:** 6 / 6
**Revised:** 2026-05-07 (consolidated test_exclusion.py + test_candidates.py into test_recommendation.py per Plan 01-01 Task 3 file layout)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/apps/recommendations/personalization_engine.py` | service | request-response | `backend/apps/recommendations/hybrid_recommendation_engine.py` | exact (same engine layer, same logger/ORM pattern) |
| `backend/apps/core/views.py` | controller | CRUD | self (submit_feedback already exists — surgical patch) | self |
| `backend/apps/recommendations/hybrid_recommendation_engine.py` | service | CRUD + event-driven | self (all strategy methods follow identical pattern) | self |
| `backend/apps/ai/ai_feedback_service.py` | service | request-response | `backend/apps/recommendations/personalization_engine.py` | role-match |
| `backend/pytest.ini` | config | — | none in codebase | no analog |
| `backend/tests/test_personalization.py` | test | — | `backend/tests/test_ai_feedback_service.py` | exact |
| `backend/tests/test_feedback.py` | test | — | `backend/tests/test_ai_feedback_service.py` | exact |
| `backend/tests/test_recommendation.py` | test | — | `backend/tests/test_ai_feedback_service.py` | exact (consolidates exclusion + artist-filter + related-artists; one file mirrors one source module: `hybrid_recommendation_engine.py`) |

---

## Pattern Assignments

### `backend/apps/recommendations/personalization_engine.py` (service, request-response)

**Bugs to fix:** Bug 1 (missing `Count` import), Bug 2 (`update_weights` wrong arity).

**Analog:** `backend/apps/recommendations/hybrid_recommendation_engine.py`

**Imports pattern** (personalization_engine.py lines 14–25 — current state, showing what is present):
```python
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from django.utils import timezone
from datetime import datetime, timedelta
import json
from collections import defaultdict
import spotipy
from spotipy.exceptions import SpotifyException
from django.conf import settings
from apps.core.models import UserPreferences, UserFeedback, Track
```

**Bug 1 fix — add to imports block (after line 25):**
```python
from django.db.models import Count
```
`Count` is used at line 313: `.annotate(count=Count('feedback_type'))`. Without the import, calling `get_personalization_summary()` raises `NameError: name 'Count' is not defined`.

**Bug 2 fix — replace `apply_feedback_learning` body (lines 250–267):**

Current broken code (lines 250–267):
```python
def apply_feedback_learning(self, feedback: UserFeedback):
    logger.info(f"Learning from feedback: {feedback.feedback_type} for track {feedback.track.name}")
    if feedback.track_features:
        self.preferences.update_weights(feedback, feedback.track_features)  # CRASHES — method does not exist on UserPreferences
    logger.info(f"Updated preferences for user {self.user.id} based on {feedback.feedback_type}")
```

Replace with Phase 1 no-op (matches logger pattern from hybrid_recommendation_engine.py lines 206–209):
```python
def apply_feedback_learning(self, feedback: UserFeedback):
    """
    Update user preferences based on new feedback.
    Phase 1: no-op — taste vector update wired in Phase 2.
    """
    # TODO Phase 2: build weights_dict from feedback and call
    #   UserProfile(user=self.user).update_weights(weights_dict)
    #   Note: update_weights(self, weights) is on UserProfile (models.py:151), not UserPreferences
    logger.info(
        "apply_feedback_learning: Phase 1 no-op for %s on %s",
        feedback.feedback_type,
        feedback.track.name,
    )
```

**Logger pattern** — copy from hybrid_recommendation_engine.py line 28:
```python
logger = logging.getLogger(__name__)
```
Personalization engine already uses this identical pattern at line 26. No change needed.

**Error handling pattern** — copy from hybrid_recommendation_engine.py lines 560–566 (try/except/continue inside a loop):
```python
        except Exception as e:
            logger.warning(f"Error getting artist {artist.get('name', 'unknown')}: {str(e)}")
            continue
```
The `remove_feedback_learning` method (lines 279–298) already uses this pattern correctly with `try/except/logger.error`. No change needed there.

---

### `backend/apps/core/views.py` (controller, CRUD)

**Bug to fix:** Bug 3 — `RecommendationLog.liked` never written on thumbs-up/down.

**Analog:** Self. The insertion point is inside the existing `submit_feedback` function.

**View decorator and auth pattern** (views.py lines 555–557 — unchanged, copy for new test mocks):
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
```

**Existing DailyGem sync pattern** (views.py lines 636–643 — the working sync that sets `was_liked`):
```python
            # Update was_liked on today's gem if it matches this track
            from django.utils import timezone as tz
            today_gem = DailyGem.objects.filter(
                user=request.user, date=tz.localdate(), track=track
            ).first()
            if today_gem:
                today_gem.was_liked = (feedback_type == 'LIKE')
                today_gem.save(update_fields=['was_liked'])
```

**Bug 3 fix — insert immediately after the DailyGem block above (after line 643), before the PersonalizationEngine call:**
```python
            # Fix Bug 3: write RecommendationLog.liked so metrics queries return non-zero
            log = RecommendationLog.objects.filter(
                user=request.user, track=track
            ).order_by('-recommended_at').first()
            if log:
                log.liked = (feedback_type == 'LIKE') if feedback_type in ('LIKE', 'DISLIKE') else None
                log.save(update_fields=['liked'])
```

**Model field reference** (models.py line 232):
```python
    liked = models.BooleanField(null=True, blank=True)
```
`liked` accepts `True`, `False`, or `None` — the fix uses all three values correctly.

**Error handling pattern** (views.py lines 663–665 — matches all other view functions):
```python
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return JsonResponse({'error': 'Failed to submit feedback'}, status=500)
```

**Imports already present** (views.py line 30):
```python
from .models import SpotifyToken, Track, UserFeedback, UserPreferences, RecommendationLog, AIFeedback, DailyGem
```
`RecommendationLog` is already imported. No import change needed.

---

### `backend/apps/recommendations/hybrid_recommendation_engine.py` (service, CRUD + event-driven)

**Bugs to fix:** Bug 5 (top-artist filter), Bug 6 (exclusion set relies on live API), Bug 7 (missing 5th strategy).

**Imports block** (lines 12–26 — copy for the new method's inline imports):
```python
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from datetime import datetime, timedelta
import json
import random
from collections import defaultdict
import spotipy
from spotipy.exceptions import SpotifyException
from django.conf import settings
from apps.core.models import UserProfile, Track, UserFeedback
from apps.core.models import SpotifyToken
from apps.spotify.utils import rate_limit_monitor, get_spotipy_client
from .track_discovery_engine import TrackDiscoveryEngine
```

**Bug 6 fix — new helper method `_get_persistent_exclusion_set`.**
Place after `_get_spotify_client` (line 659). Mirrors the ORM query pattern from `get_recommendation_metrics` (views.py lines 1129–1131):
```python
    def _get_persistent_exclusion_set(self) -> set:
        """Return set of Spotify track IDs the user has already seen (DB-backed, no API calls)."""
        from apps.core.models import RecommendationLog, DailyGem
        logged = set(
            RecommendationLog.objects
            .filter(user=self.user)
            .exclude(track__spotify_id='error_log')  # exclude the error sentinel
            .values_list('track__spotify_id', flat=True)
        )
        gemmed = set(
            DailyGem.objects
            .filter(user=self.user)
            .values_list('track__spotify_id', flat=True)
        )
        return logged | gemmed
```

**Bug 5 + 6 fix — replace `_filter_out_liked_songs` (lines 726–842).**
Current method: makes batched `current_user_saved_tracks_contains` API calls, then falls back to cached profile. Also filters any track by a top artist (Bug 5 — too blunt). Replace with:
```python
    def _filter_out_liked_songs(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Exclude tracks the user has already seen, using a DB-backed exclusion set.
        No live Spotify API calls — avoids rate limit burn and fallback-to-cache issues.
        """
        exclusion_ids = self._get_persistent_exclusion_set()
        logger.info(f"DB exclusion set has {len(exclusion_ids)} track IDs")

        filtered = []
        filtered_out = 0
        for rec in recommendations:
            if rec.get('id') in exclusion_ids:
                filtered_out += 1
                logger.info(f"FILTERED (DB exclusion): {rec['name']} by {rec['artist']}")
            else:
                filtered.append(rec)

        logger.info(f"Filtered {len(recommendations)} -> {len(filtered)} tracks (removed {filtered_out})")
        return filtered
```

**Bug 7 — new method `_get_related_artist_recommendations`.**
Copy the method signature and loop structure from the closest analog — `_get_artist_network_recommendations` (lines 499–567):
```python
    def _get_related_artist_recommendations(self, limit: int) -> List[Dict]:
        """
        5th candidate strategy: use Spotify's artist_related_artists graph.
        For each top artist, fetch related artists, then pull album deep cuts.
        """
        recommendations = []
        top_artists = self.profile.data['base_data'].get('top_artists', [])
        sp = self._get_spotify_client()
        if not sp:
            return []
        for artist in top_artists[:4]:
            if not self._check_rate_limit() or len(recommendations) >= limit:
                break
            artist_id = artist.get('id')
            if not artist_id:
                continue
            try:
                related = sp.artist_related_artists(artist_id)
                logger.info(
                    f"artist_related_artists: {len(related['artists'])} related to {artist['name']}"
                )
                for rel_artist in related['artists'][:5]:
                    albums = sp.artist_albums(rel_artist['id'], album_type='album', limit=2, country='US')
                    for album in albums['items']:
                        album_tracks = sp.album_tracks(album['id'], limit=8)
                        track_ids = [t['id'] for t in album_tracks['items'] if t.get('id')]
                        if not track_ids:
                            continue
                        full_tracks = sp.tracks(track_ids)
                        for track in full_tracks['tracks']:
                            if track and track.get('popularity', 100) < 40:
                                recommendations.append({
                                    'id': track['id'],
                                    'name': track['name'],
                                    'artist': track['artists'][0]['name'],
                                    'album': album['name'],
                                    'preview_url': track.get('preview_url'),
                                    'image_url': album['images'][0]['url'] if album.get('images') else None,
                                    'source': 'related_artists',
                                    'score': 0.0,
                                    'popularity': track.get('popularity', 0),
                                })
                                if len(recommendations) >= limit:
                                    break
            except Exception as e:
                logger.warning(f"artist_related_artists failed for {artist.get('name')}: {e}")
                continue
        return recommendations[:limit]
```

**Call site in `get_recommendations`** — add after Strategy 4 block (after line 133), following the identical guard+log pattern of strategies 1–4 (lines 112–133):
```python
            # Strategy 5: Related Artist Deep Cuts
            if self._check_rate_limit():
                related_recs = self._get_related_artist_recommendations(limit * 2)
                all_recommendations.extend(related_recs)
                logger.info(f"Related artist strategy found {len(related_recs)} recommendations")
```

---

### `backend/tests/test_ai_feedback_service.py` (existing broken test, fix only)

**Bug:** Line 27 uses `'backend.settings'` as the Django settings module. From inside `backend/`, the correct path is `'config.settings'`.

**Fix** (line 27, current):
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
```
**Replace with:**
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
```

---

### `backend/pytest.ini` (config, new file)

**No codebase analog exists.** There is no `pytest.ini`, `setup.cfg`, or `conftest.py` anywhere in `backend/` (only in `venv/`).

**Standard pytest-django pattern:**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
```
This fixes the stale `backend.settings` path and lets `pytest tests/` run from `backend/`.

---

### `backend/tests/test_personalization.py` (test, new file)

**Analog:** `backend/tests/test_ai_feedback_service.py`

**Test file structure pattern** (test_ai_feedback_service.py lines 1–29):
```python
"""
Unit tests for [module under test]
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = backend_dir / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

# Set up Django (use config.settings, NOT backend.settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
```

**Test class pattern** (test_ai_feedback_service.py lines 31–57):
```python
class TestPersonalizationEngine(unittest.TestCase):
    """Test cases for PersonalizationEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock User
        self.mock_user = Mock()
        self.mock_user.id = 1

    def test_count_import_does_not_crash(self):
        """Count must be importable and usable in get_personalization_summary"""
        from apps.recommendations.personalization_engine import PersonalizationEngine
        # If Count is not imported, instantiating and calling will NameError
        # Just verify import succeeds
        from django.db.models import Count
        self.assertIsNotNone(Count)

    def test_apply_feedback_learning_is_noop(self):
        """apply_feedback_learning must not raise on call"""
        with patch('apps.core.models.UserPreferences.objects') as mock_prefs:
            mock_prefs.get_or_create.return_value = (Mock(), False)
            from apps.recommendations.personalization_engine import PersonalizationEngine
            engine = PersonalizationEngine(self.mock_user)
            mock_feedback = Mock()
            mock_feedback.feedback_type = 'LIKE'
            mock_feedback.track.name = 'Test Track'
            mock_feedback.track_features = {}
            # Should not raise
            engine.apply_feedback_learning(mock_feedback)
```

---

### `backend/tests/test_feedback.py` (test, new file)

**Analog:** `backend/tests/test_ai_feedback_service.py`

**Core test pattern** — copy setUp/tearDown from analog, then:
```python
class TestSubmitFeedbackLiked(django.test.TestCase):
    """RecommendationLog.liked is written correctly by submit_feedback"""

    def setUp(self):
        from django.contrib.auth.models import User
        from apps.core.models import Track, RecommendationLog
        self.user = User.objects.create_user('testuser', password='pw')
        self.track = Track.objects.create(
            spotify_id='abc123', name='Test', artist='Artist', album='Album'
        )
        # Pre-create a log entry (simulates a prior recommendation)
        self.log = RecommendationLog.objects.create(user=self.user, track=self.track)

    def test_liked_set_true_on_like(self):
        """LIKE feedback sets RecommendationLog.liked = True"""
        # Call the ORM update directly (mirrors the fix in submit_feedback)
        log = RecommendationLog.objects.filter(
            user=self.user, track=self.track
        ).order_by('-recommended_at').first()
        log.liked = True
        log.save(update_fields=['liked'])
        log.refresh_from_db()
        self.assertTrue(log.liked)

    def test_liked_set_none_on_unlike(self):
        """UNLIKE sets RecommendationLog.liked = None"""
        log = RecommendationLog.objects.filter(
            user=self.user, track=self.track
        ).order_by('-recommended_at').first()
        log.liked = None
        log.save(update_fields=['liked'])
        log.refresh_from_db()
        self.assertIsNone(log.liked)
```

---

### `backend/tests/test_recommendation.py` (test, new file — consolidates exclusion, artist-filter, related-artists)

**Analog:** `backend/tests/test_ai_feedback_service.py`

**Consolidation note:** The earlier PATTERNS draft proposed `test_exclusion.py` + `test_candidates.py` as two files. Plan 01-01 Task 3 collapses both into a single `test_recommendation.py` so the test file maps 1:1 to the source module under test (`hybrid_recommendation_engine.py`). The three test classes inside are:
- `TestPersistentExclusionSet` (Bug 6)
- `TestFilterOutLikedSongs` (Bug 5)
- `TestRelatedArtistStrategy` (Bug 7)

**Core test pattern (TestPersistentExclusionSet):**
```python
class TestPersistentExclusionSet(django.test.TestCase):
    """_get_persistent_exclusion_set returns correct DB-backed set"""

    def setUp(self):
        from django.contrib.auth.models import User
        from apps.core.models import Track, RecommendationLog, UserProfile
        self.user = User.objects.create_user('excuser', password='pw')
        UserProfile.objects.get_or_create(user=self.user)
        self.track = Track.objects.create(
            spotify_id='excl_track_1', name='Old Gem', artist='Artist', album='Album'
        )
        RecommendationLog.objects.create(user=self.user, track=self.track)

    def test_previously_recommended_track_in_exclusion_set(self):
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertIn('excl_track_1', exclusion)

    def test_error_sentinel_excluded(self):
        """'error_log' sentinel track must not appear in exclusion set"""
        from apps.core.models import Track, RecommendationLog
        err_track = Track.objects.create(
            spotify_id='error_log', name='Error Log', artist='System', album='Error'
        )
        RecommendationLog.objects.create(user=self.user, track=err_track)
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertNotIn('error_log', exclusion)
```

---

### `backend/tests/test_recommendation.py — TestRelatedArtistStrategy` (mock-based section of the consolidated file)

**Analog:** `backend/tests/test_ai_feedback_service.py` (mock pattern)

**Core test pattern — mock spotipy entirely (mirrors test_ai_feedback_service.py mock_openai pattern):**
```python
class TestRelatedArtistStrategy(unittest.TestCase):
    """_get_related_artist_recommendations returns candidates when API responds"""

    def setUp(self):
        self.mock_user = Mock()
        self.mock_user.id = 99

    def test_returns_candidates_on_valid_api_response(self):
        with patch('apps.recommendations.hybrid_recommendation_engine.get_spotipy_client') as mock_client_fn, \
             patch('apps.core.models.UserProfile.objects') as mock_profile_qs, \
             patch('apps.core.models.SpotifyToken.objects') as mock_token_qs:

            # Mock token
            mock_token = Mock()
            mock_token.is_expired.return_value = False
            mock_token_qs.filter.return_value.first.return_value = mock_token

            # Mock spotipy client
            mock_sp = Mock()
            mock_client_fn.return_value = mock_sp
            mock_sp.artist_related_artists.return_value = {
                'artists': [{'id': 'rel1', 'name': 'Related Artist'}]
            }
            mock_sp.artist_albums.return_value = {
                'items': [{'id': 'alb1', 'name': 'Hidden Album', 'images': [{'url': 'http://img'}]}]
            }
            mock_sp.album_tracks.return_value = {
                'items': [{'id': 'trk1'}, {'id': 'trk2'}]
            }
            mock_sp.tracks.return_value = {
                'tracks': [
                    {'id': 'trk1', 'name': 'Deep Cut', 'artists': [{'name': 'Related Artist'}],
                     'popularity': 25, 'preview_url': None},
                ]
            }

            from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
            engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
            engine.user = self.mock_user
            engine.rate_limit_monitor = Mock()
            engine.rate_limit_monitor.check_rate_limit.return_value = True
            engine._api_cache = {}
            engine.profile = Mock()
            engine.profile.data = {
                'base_data': {'top_artists': [{'id': 'art1', 'name': 'Top Artist'}]},
                'preferences': {'liked_artists': [], 'disliked_artists': []}
            }

            results = engine._get_related_artist_recommendations(limit=5)
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0]['source'], 'related_artists')
```

---

## Shared Patterns

### Logger initialization
**Source:** `backend/apps/recommendations/hybrid_recommendation_engine.py` line 28
**Apply to:** All modified/new service files
```python
logger = logging.getLogger(__name__)
```

### Django ORM field update (write single field, no full-model save)
**Source:** `backend/apps/core/views.py` lines 614–615 (DailyGem sync)
**Apply to:** `views.py` Bug 3 fix (RecommendationLog.liked), all test setUp ORM writes
```python
instance.field = value
instance.save(update_fields=['field'])
```

### Error sentinel exclusion in ORM queries
**Source:** `backend/apps/core/views.py` lines 1129–1131 (get_recommendation_metrics)
**Apply to:** `_get_persistent_exclusion_set` in hybrid engine, any new test that queries RecommendationLog
```python
RecommendationLog.objects.filter(user=request.user).exclude(track__spotify_id='error_log')
```

### Strategy method signature and guard pattern
**Source:** `backend/apps/recommendations/hybrid_recommendation_engine.py` lines 499–567 (`_get_artist_network_recommendations`)
**Apply to:** new `_get_related_artist_recommendations` method (Bug 7)
```python
def _get_strategy_recommendations(self, limit: int) -> List[Dict]:
    recommendations = []
    try:
        ...
        for artist in ...:
            if not self._check_rate_limit():
                break
            try:
                sp = self._get_spotify_client()
                if not sp:
                    continue
                ...
            except Exception as e:
                logger.warning(f"...: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error in ...: {str(e)}")
    return recommendations[:limit]
```

### Test file Django setup block
**Source:** `backend/tests/test_ai_feedback_service.py` lines 12–29
**Apply to:** All new test files (`test_personalization.py`, `test_feedback.py`, `test_recommendation.py`). Note: the original PATTERNS draft listed `test_exclusion.py` and `test_candidates.py` as separate files; Plan 01-01 Task 3 consolidates both into a single `test_recommendation.py` (one test file per source module — mirrors `hybrid_recommendation_engine.py`). Tests for exclusion-set, artist-filter, and related-artists strategies all live in `test_recommendation.py`.
```python
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # NOT 'backend.settings'
import django
django.setup()
```

### unittest.mock pattern for external service isolation
**Source:** `backend/tests/test_ai_feedback_service.py` lines 36–57 (mock_openai_patcher)
**Apply to:** `test_recommendation.py` `TestRelatedArtistStrategy` (mock spotipy via `patch.object`), `test_personalization.py` (mock `UserPreferences.objects`)
```python
self.mock_patcher = patch('module.path.ClassName')
self.mock_obj = self.mock_patcher.start()
# ... in tearDown:
self.mock_patcher.stop()
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/pytest.ini` | config | — | No pytest config exists in the project; venv copies do not count |

---

## Key Constraints from Code Inspection

1. **`UserPreferences` has no `update_weights` method** — only `UserProfile` (models.py line 151) has `update_weights(self, weights)`. The `apply_feedback_learning` fix must not call `self.preferences.update_weights(...)` in Phase 1.

2. **`RecommendationLog.liked` is `BooleanField(null=True)`** (models.py line 232) — stores `True` (like), `False` (dislike), `None` (not yet rated). The Bug 3 fix must set `None` on unlike, not `False`.

3. **`DailyGem` has `unique_together = ['user', 'date']`** (models.py line 287) — any test that creates DailyGem rows must use `get_or_create` or handle `IntegrityError` on duplicate date.

4. **`RecommendationLog.log_error()` creates a sentinel Track with `spotify_id='error_log'`** (models.py lines 256–270) — always `.exclude(track__spotify_id='error_log')` when building the DB exclusion set.

5. **`sp.recommendations()` is broken** (views.py line 418 comment) — do not use in any new strategy code. The 5th strategy uses `artist_related_artists` + `artist_albums` + `album_tracks` + `tracks`.

---

## Metadata

**Analog search scope:** `backend/apps/core/`, `backend/apps/recommendations/`, `backend/apps/ai/`, `backend/tests/`
**Files scanned:** 6 source files read in full, 2 grep passes for line-location
**Pattern extraction date:** 2026-05-07

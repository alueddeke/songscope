# Phase 3: Feedback Learning Loop - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 9 files (5 modify, 4 create)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/apps/recommendations/personalization_engine.py` | service | event-driven | same file — `apply_feedback_learning()` no-op body (lines 251–268) | exact — activate existing no-op skeleton |
| `backend/apps/recommendations/hybrid_recommendation_engine.py` | service | transform | same file — `_score_recommendations()` (lines 753–787), `remove_feedback()` (lines 881–905) | exact — same class, same data shapes |
| `backend/apps/ai/ai_feedback_service.py` | service | request-response | same file — `FeedbackInterpreter` class (lines 65–205) | exact — add sibling class with same init/fallback pattern |
| `backend/apps/core/models.py` | model | CRUD | `UserProfile.data` JSONField; `DailyGem` model (lines ~280+); RESEARCH.md line citations | exact — no new model fields needed (Phase 3 uses JSONField keys only) |
| `backend/apps/core/views.py` | controller | request-response | same file — existing `@api_view` / `@permission_classes` pattern (Phase 2 PATTERNS.md lines 290–314) | exact — add new view following same decorator + JsonResponse pattern |
| `backend/apps/recommendations/tests/test_personalization_engine.py` | test | event-driven | Phase 2 `backend/tests/test_scoring.py` — `__new__` bypass + `unittest.TestCase` pattern | exact — same bypass, same profile mock structure |
| `backend/apps/recommendations/tests/test_bandit.py` | test | transform | Phase 2 `backend/tests/test_scoring.py` — mock-based `unittest.TestCase` | exact — pure computation tests with mocked profile |
| `backend/apps/recommendations/tests/test_popularity_targeting.py` | test | transform | Phase 2 `backend/tests/test_scoring.py` — mock-based `unittest.TestCase` | exact — pure computation tests with mocked profile |
| `backend/apps/core/tests/test_daily_gem_view.py` | test | request-response | Phase 2 `backend/tests/test_scoring.py` `TestRecommendationLogSource` — Django `TestCase` with DB | exact — DB-backed `django.test.TestCase` pattern |

---

## Pattern Assignments

### `personalization_engine.py` — `apply_feedback_learning()` and `remove_feedback_learning()` (modify)

**Analog:** Same file — the existing no-op skeleton at lines 251–281.

**Existing no-op skeleton to replace** (lines 251–281):
```python
def apply_feedback_learning(self, feedback: UserFeedback):
    """
    Update user preferences based on new feedback.
    ...
    """
    logger.info(
        "apply_feedback_learning: Phase 1 no-op for %s on %s",
        feedback.feedback_type,
        feedback.track.name,
    )

def remove_feedback_learning(self, track_id: str):
    """Remove learning effects when a user unlikes a track."""
    logger.info(f"Removing feedback learning for track {track_id}")
    # Learning reversal will be wired in Phase 2.
    logger.info(f"Removing feedback learning for track {track_id}")
```

**Imports block** (lines 1–27 of `personalization_engine.py`) — already has what's needed; add one import:
```python
# Already present:
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
from django.db.models import Count
from apps.core.models import UserPreferences, UserFeedback, Track

logger = logging.getLogger(__name__)

# ADD — needed for UserProfile fetch inside the methods:
# (import inside the method body to avoid circular imports, same pattern as RESEARCH.md Pattern 1)
# from apps.core.models import UserProfile
```

**Critical constraints from RESEARCH.md Pitfall 2:**
- `PersonalizationEngine.__init__` sets only `self.user` and `self.preferences` (a `UserPreferences` object)
- There is NO `self.profile` attribute — do NOT use it
- Fetch `UserProfile` locally inside each method: `UserProfile.objects.get(user=self.user)`

**`apply_feedback_learning()` replacement** (verified pattern — RESEARCH.md Pattern 1, lines 183–221):
```python
def apply_feedback_learning(self, feedback: UserFeedback):
    """
    Online update: taste vector + popularity midpoint + bandit source stats.
    Called from submit_feedback view on every LIKE/DISLIKE.
    """
    from apps.core.models import UserProfile, RecommendationLog

    lr = 0.1
    try:
        profile = UserProfile.objects.get(user=self.user)
    except UserProfile.DoesNotExist:
        logger.warning(
            "apply_feedback_learning: no UserProfile for user %s", self.user.id
        )
        return

    data = profile.data
    taste_vector = data.setdefault('taste_vector', {})

    # Genres from Track.genres ORM field — NOT from track_info dict (which has no genres key)
    # Verified: views.py line 449 sets track.genres = artist_info['genres'] on track creation
    genres = list(feedback.track.genres or [])
    signal = 1.0 if feedback.feedback_type in ('LIKE', 'SAVE') else -1.0

    # D-03: taste vector online SGD
    for genre in genres:
        taste_vector[genre] = taste_vector.get(genre, 0.0) + lr * signal

    # D-12: popularity midpoint exponential moving average
    prefs = data.setdefault('preferences', {})
    pop_range = prefs.setdefault(
        'preferred_popularity_range', {'midpoint': 30, 'width': 20}
    )
    track_pop = feedback.track.popularity or 50
    pop_range['midpoint'] += lr * (track_pop - pop_range['midpoint']) * signal

    # D-07: bandit source stats update
    BANDIT_SOURCES = [
        'playlist_mining', 'artist_network', 'genre_search',
        'related_artists', 'contextual',
    ]
    source_stats = data.setdefault(
        'source_stats', {src: {'s': 0, 'f': 0} for src in BANDIT_SOURCES}
    )
    # Look up which source produced this track (via RecommendationLog)
    log = RecommendationLog.objects.filter(
        user=self.user, track=feedback.track
    ).order_by('-recommended_at').first()
    source = log.source if log else None
    if source and source in source_stats:
        if feedback.feedback_type in ('LIKE', 'SAVE'):
            source_stats[source]['s'] += 1
        else:
            source_stats[source]['f'] += 1

    profile.data = data
    profile.save(update_fields=['data'])
    logger.info(
        "apply_feedback_learning: updated taste_vector(%d genres), midpoint=%.1f, source=%s",
        len(genres), pop_range['midpoint'], source,
    )
```

**`remove_feedback_learning()` replacement** (RESEARCH.md Pattern 4, lines 289–326):
```python
def remove_feedback_learning(self, track_id: str):
    """
    Reverse taste vector + popularity midpoint shift when user unlikes a track.
    Called from submit_feedback view BEFORE hybrid_engine.remove_feedback().
    NOTE: track_id is a spotify_id string (str), not a UserFeedback ORM object.
    """
    from apps.core.models import UserProfile, Track

    lr = 0.1
    try:
        profile = UserProfile.objects.get(user=self.user)
    except UserProfile.DoesNotExist:
        return

    track = Track.objects.filter(spotify_id=track_id).first()
    if not track:
        logger.warning("remove_feedback_learning: Track %s not found", track_id)
        return

    # Find original feedback type from history to know the original signal direction
    history = profile.data.get('preferences', {}).get('feedback_history', [])
    original_entry = next(
        (e for e in reversed(history) if e.get('track_id') == track_id), None
    )
    if not original_entry:
        logger.warning("remove_feedback_learning: no history entry for %s", track_id)
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
    track_pop = track.popularity or 50
    pop_range['midpoint'] -= lr * (track_pop - pop_range['midpoint']) * signal

    profile.save(update_fields=['data'])
    logger.info("remove_feedback_learning: reversed update for track %s", track_id)
```

---

### `hybrid_recommendation_engine.py` — `_score_recommendations()`, `get_recommendation_weights()`, `add_feedback()`, `remove_feedback()` (modify)

**Analog:** Same file — existing methods at lines 753–905.

**Existing `_score_recommendations()` to modify** (lines 753–787 — already read, full body in context):
```python
def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
    """Score candidates: 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier (LOCKED formula)"""
    taste_vector = self.profile.data.get('taste_vector', {})
    liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
    disliked_artists = self.profile.data.get('preferences', {}).get('disliked_artists', [])

    artist_genre_lookup = {
        a['name']: a.get('genres', [])
        for a in self.profile.data.get('base_data', {}).get('top_artists', [])
    }

    for rec in recommendations:
        artist_name = rec.get('artist', '')
        candidate_genres = {g: 1.0 for g in artist_genre_lookup.get(artist_name, [])}
        genre_sim = self._cosine_similarity(candidate_genres, taste_vector)

        # CHANGE THIS LINE ONLY:
        novelty = 1.0 - (rec.get('popularity', 50) / 100.0)  # <-- replace with bell-curve

        if artist_name in liked_artists:
            feedback_multiplier = 1.5
        elif artist_name in disliked_artists:
            feedback_multiplier = 0.5
        else:
            feedback_multiplier = 1.0

        # LOCKED formula — add one post-score multiplier line:
        rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations
```

**Novelty line replacement** (D-10 — bell-curve novelty, RESEARCH.md Pattern 2):
```python
# Replace:
#   novelty = 1.0 - (rec.get('popularity', 50) / 100.0)
# With:
import math  # add to file-level imports (math is stdlib)

def _bell_curve_novelty(self, popularity: int, midpoint: float, width: float) -> float:
    """Gaussian novelty peaked at midpoint. Returns 0.0–1.0."""
    return math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))

# Inside _score_recommendations(), after building artist_genre_lookup:
pop_range = self.profile.data.get('preferences', {}).get(
    'preferred_popularity_range', {'midpoint': 30, 'width': 20}
)
novelty = self._bell_curve_novelty(
    rec.get('popularity', 50),
    pop_range['midpoint'],
    pop_range['width'],
)
```

**Bandit post-score multiplier** (RESEARCH.md Option A — recommended, preserves locked formula):
```python
# After LOCKED formula line, add one line:
source_weights = self.get_recommendation_weights()
rec['score'] = (0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier) \
               * source_weights.get(rec.get('source', ''), 1.0)

# Also collect score_breakdown for the top track:
rec['_score_breakdown'] = {
    'genre_sim': round(genre_sim, 4),
    'novelty': round(novelty, 4),
    'feedback_multiplier': round(feedback_multiplier, 4),
    'top_genres': sorted(taste_vector, key=taste_vector.get, reverse=True)[:3],
}
```

**`get_recommendation_weights()` — bandit replacement** (D-08, RESEARCH.md Pattern 3):
- CRITICAL: This method currently lives on `UserProfile` model (Phase 2 PATTERNS.md line 947), not on `HybridRecommendationEngine`. The bandit sampling belongs in `HybridRecommendationEngine` because it needs `self.profile.data['source_stats']`. Add a NEW `get_recommendation_weights()` method to `HybridRecommendationEngine` that shadows the model-level method.

```python
BANDIT_SOURCES = [
    'playlist_mining', 'artist_network', 'genre_search',
    'related_artists', 'contextual',
]
COLD_START_N = 3  # observations per source before bandit overrides static defaults

def get_recommendation_weights(self) -> Dict[str, float]:
    """
    Thompson Sampling bandit: sample Beta(s+1, f+1) per source.
    Falls back to static defaults until COLD_START_N observations per source.
    """
    STATIC_DEFAULTS = {
        'playlist_mining': 0.3,
        'artist_network': 0.25,
        'contextual': 0.2,
        'genre_search': 0.15,
        'related_artists': 0.1,
    }
    source_stats = self.profile.data.get('source_stats', {})
    weights = {}
    for source in BANDIT_SOURCES:
        stats = source_stats.get(source, {'s': 0, 'f': 0})
        total = stats['s'] + stats['f']
        if total < COLD_START_N:
            weights[source] = STATIC_DEFAULTS.get(source, 0.1)
        else:
            weights[source] = float(np.random.beta(stats['s'] + 1, stats['f'] + 1))
    return weights
```

**`add_feedback()` and `remove_feedback()` — current bodies** (lines 876–905, already read):
```python
def add_feedback(self, track_id: str, feedback_type: str, track_info: Dict = None):
    """Add user feedback and update profile"""
    self.profile.add_feedback(track_id, feedback_type, track_info)
    logger.info(f"Added feedback: {feedback_type} for track {track_id}")

def remove_feedback(self, track_id: str):
    """Remove user feedback from profile"""
    try:
        feedback_history = self.profile.data.get('preferences', {}).get('feedback_history', [])
        updated_history = [fb for fb in feedback_history if fb.get('track_id') != track_id]
        if 'preferences' not in self.profile.data:
            self.profile.data['preferences'] = {}
        self.profile.data['preferences']['feedback_history'] = updated_history
        liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
        if entry := next((fb for fb in feedback_history if fb.get('track_id') == track_id), None):
            artist_name = entry.get('track_info', {}).get('artist')
            if artist_name and artist_name in liked_artists:
                liked_artists.remove(artist_name)
                self.profile.data['preferences']['liked_artists'] = liked_artists
        self.profile.save()
        logger.info(f"Removed feedback for track {track_id}")
    except Exception as e:
        logger.error(f"Error removing feedback: {str(e)}")
```
These methods do NOT need changes for Phase 3 — `PersonalizationEngine` methods hook in at the view level, called alongside (not inside) these engine methods.

---

### `ai_feedback_service.py` — `RecommendationExplainer` class (modify — add new class)

**Analog:** Same file — `FeedbackInterpreter` class (lines 65–205, fully read in context).

**Init pattern to copy exactly** (lines 68–86):
```python
class FeedbackInterpreter:
    def __init__(self):
        self.rate_limiter = RateLimitMonitor()
        self.openai_client = None
        self._initialize_openai()

    def _initialize_openai(self):
        """Initialize OpenAI client if API key is available"""
        try:
            from openai import OpenAI
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found in settings")
        except ImportError:
            logger.error("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
```

**OpenAI call pattern to copy** (lines 107–135):
```python
if not self.openai_client:
    logger.warning("OpenAI client not available, using fallback interpretation")
    return self._fallback_interpretation(user_text)

if not self.rate_limiter.check_openai_limit():
    raise RateLimitExceeded("OpenAI rate limit exceeded")

try:
    response = self.openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.1
    )
    tokens_used = response.usage.total_tokens
    self.rate_limiter.log_cost(tokens_used)
    content = response.choices[0].message.content
    ...
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse OpenAI response: {str(e)}")
    return self._fallback_interpretation(user_text)
except Exception as e:
    logger.error(f"OpenAI request failed: {str(e)}")
    return self._fallback_interpretation(user_text)
```

**`RecommendationExplainer` new class to add after `FeedbackInterpreter`** (D-13, RESEARCH.md Pattern 6):
```python
class RecommendationExplainer:
    """Generate natural language explanations for recommended tracks, citing score components."""

    def __init__(self):
        self.rate_limiter = RateLimitMonitor()
        self.openai_client = None
        self._initialize_openai()  # reuse identical _initialize_openai pattern

    def _initialize_openai(self):
        """Initialize OpenAI client — same pattern as FeedbackInterpreter."""
        try:
            from openai import OpenAI
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("RecommendationExplainer: OpenAI client initialized")
            else:
                logger.warning("RecommendationExplainer: OPENAI_API_KEY not set")
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"RecommendationExplainer init error: {str(e)}")

    def generate_explanation(self, track_info: dict, score_breakdown: dict) -> str:
        """
        Generate natural language explanation for why this track was recommended.

        Args:
            track_info: {name, artist, album, popularity}
            score_breakdown: {genre_sim: float, novelty: float,
                              feedback_multiplier: float, top_genres: list[str]}
        Returns:
            Explanation string (natural language).
        """
        if not self.openai_client:
            return self._fallback_explanation(track_info, score_breakdown)

        if not self.rate_limiter.check_openai_limit():
            return self._fallback_explanation(track_info, score_breakdown)

        try:
            prompt = self._build_prompt(track_info, score_breakdown)
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7,
            )
            self.rate_limiter.log_cost(response.usage.total_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"RecommendationExplainer.generate_explanation error: {str(e)}")
            return self._fallback_explanation(track_info, score_breakdown)

    def _build_prompt(self, track_info: dict, score_breakdown: dict) -> str:
        top_genres = ", ".join(score_breakdown.get('top_genres', [])) or "various genres"
        return (
            f"Explain in 2 sentences why '{track_info.get('name')}' by "
            f"'{track_info.get('artist')}' is a great hidden gem recommendation. "
            f"Use these score components naturally: genre match score {score_breakdown.get('genre_sim', 0):.0%}, "
            f"novelty score {score_breakdown.get('novelty', 0):.0%} "
            f"(popularity {track_info.get('popularity', '?')}), "
            f"listener affinity {score_breakdown.get('feedback_multiplier', 1.0):.1f}x, "
            f"top matching genres: {top_genres}. "
            f"Write as if speaking to the listener. Do not mention numbers directly."
        )

    def _fallback_explanation(self, track_info: dict, score_breakdown: dict) -> str:
        top_genres = score_breakdown.get('top_genres', [])
        genre_str = f" in {', '.join(top_genres[:2])}" if top_genres else ""
        return (
            f"We think you'll love '{track_info.get('name')}' by "
            f"{track_info.get('artist')}{genre_str} — it's a hidden gem that "
            f"matches your taste profile with a strong genre similarity and novelty score."
        )
```

---

### `models.py` — `UserProfile.data` schema (no code changes needed)

**Analog:** Existing `UserProfile.data` JSONField — `setdefault` pattern used in `apply_feedback_learning()` handles initialization at runtime. No migration required.

**New JSON keys added at runtime** (D-07, D-11):
```python
# New key: source_stats — initialized by setdefault in apply_feedback_learning()
UserProfile.data['source_stats'] = {
    'playlist_mining': {'s': 0, 'f': 0},
    'artist_network':  {'s': 0, 'f': 0},
    'genre_search':    {'s': 0, 'f': 0},
    'related_artists': {'s': 0, 'f': 0},
    'contextual':      {'s': 0, 'f': 0},
}

# New key: preferred_popularity_range — initialized by setdefault in apply_feedback_learning()
UserProfile.data['preferences']['preferred_popularity_range'] = {
    'midpoint': 30,  # biased toward low-popularity hidden gems
    'width': 20,
}
```

**Save pattern** (established across all phases — verified in RESEARCH.md):
```python
profile.data = data
profile.save(update_fields=['data'])
```

**DailyGem model note** (RESEARCH.md Pitfall 5): `DailyGem` has no `score_breakdown` field. For Phase 3, return `score_breakdown` in the API response without persisting it (simpler, no migration). If Phase 4 needs historical breakdowns, add `score_breakdown = models.JSONField(default=dict, blank=True)` then.

---

### `views.py` — `/api/daily-gem/` new view + URLconf (modify)

**Analog:** Same file — existing `@api_view` + `@permission_classes([IsAuthenticated])` views. Phase 2 PATTERNS.md lines 290–314 confirm the decorator stack and `JsonResponse` pattern.

**Existing view decorator pattern** (from Phase 2 PATTERNS.md, verified at views.py lines 327–336):
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def some_view(request):
    ...
    return JsonResponse({...})
```

**Required imports to confirm present** (from `hybrid_recommendation_engine.py` line 23-24, which already imports these):
```python
from apps.core.models import UserProfile, Track, UserFeedback, DailyGem, RecommendationLog
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
from apps.ai.ai_feedback_service import RecommendationExplainer
```

**`get_daily_gem` view to add** (D-14, RESEARCH.md Pattern 7):
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_gem(request):
    """
    Return today's daily gem recommendation with explanation and score breakdown.
    Caches in DailyGem model; regenerates if force_new=true query param present.
    """
    force_new = request.GET.get('force_new', 'false').lower() == 'true'
    today = timezone.localdate()

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
                'score_breakdown': None,  # not persisted; regenerated on force_new
                'date': str(today),
                'cached': True,
            })

    try:
        engine = HybridRecommendationEngine(request.user)
        recs = engine.get_recommendations(limit=20, force_fresh=force_new)
        if not recs:
            return JsonResponse({'error': 'No recommendations available'}, status=503)

        top = recs[0]
        score_breakdown = top.get('_score_breakdown', {
            'genre_sim': 0.0, 'novelty': 0.0,
            'feedback_multiplier': 1.0, 'top_genres': [],
        })

        explainer = RecommendationExplainer()
        explanation = explainer.generate_explanation(
            track_info={
                'name': top.get('name'), 'artist': top.get('artist'),
                'album': top.get('album'), 'popularity': top.get('popularity'),
            },
            score_breakdown=score_breakdown,
        )

        # Upsert DailyGem record
        track_obj, _ = Track.objects.get_or_create(
            spotify_id=top['id'],
            defaults={
                'name': top.get('name', ''),
                'artist': top.get('artist', ''),
                'album': top.get('album', ''),
            }
        )
        gem, _ = DailyGem.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={
                'track': track_obj,
                'explanation': explanation,
                'track_popularity': top.get('popularity', 0),
                'image_url': top.get('image_url', ''),
                'preview_url': top.get('preview_url', ''),
            }
        )

        return JsonResponse({
            'track': {
                'id': top['id'],
                'name': top.get('name'),
                'artist': top.get('artist'),
                'album': top.get('album'),
                'popularity': top.get('popularity'),
                'image_url': top.get('image_url'),
                'preview_url': top.get('preview_url'),
            },
            'explanation': explanation,
            'score_breakdown': score_breakdown,
            'date': str(today),
            'cached': False,
        })

    except Exception as e:
        logger.error(f"get_daily_gem error: {str(e)}")
        return JsonResponse({'error': 'Failed to generate daily gem'}, status=500)
```

**URLconf addition** (`config/urls.py` — RESEARCH.md confirms `/api/daily-gem/` is ABSENT):
```python
# Add to urlpatterns alongside existing api/ paths:
path('api/daily-gem/', views.get_daily_gem, name='daily_gem'),
```

---

### Test Files (create — 4 new files)

**Canonical test structure** (from Phase 2 PATTERNS.md — verified against `backend/tests/test_scoring.py` and `test_recommendation.py`):

#### `backend/apps/recommendations/tests/test_personalization_engine.py`

**Analog:** Phase 2 `backend/tests/test_scoring.py` — `__new__` bypass for engine tests, plus Django `TestCase` for DB-backed tests.

**Imports and conftest** (copy from Phase 2 PATTERNS.md lines 322–351):
```python
"""Tests for PersonalizationEngine.apply_feedback_learning() and remove_feedback_learning()."""
import unittest
from unittest.mock import Mock, patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import UserProfile, UserFeedback, Track
from apps.recommendations.personalization_engine import PersonalizationEngine
```

**`PersonalizationEngine` bypass pattern** (no `__new__` needed — `__init__` just calls `UserPreferences.objects.get_or_create`, which can be patched):
```python
class TestTasteVectorUpdate(TestCase):
    """D-01, D-02, D-03: apply_feedback_learning updates taste_vector online."""

    def setUp(self):
        self.user = User.objects.create_user('tvuser', password='pw')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'data': {
                'taste_vector': {},
                'preferences': {'feedback_history': []},
            }},
        )
        self.track = Track.objects.create(
            spotify_id='tv_track_1',
            name='Test Track',
            artist='Test Artist',
            album='Test Album',
            genres=['indie rock', 'folk'],
            popularity=25,
        )

    def _make_engine(self):
        from apps.core.models import UserPreferences
        # patch get_or_create so __init__ doesn't hit DB
        with patch.object(UserPreferences.objects, 'get_or_create') as mock_goc:
            mock_goc.return_value = (Mock(), False)
            engine = PersonalizationEngine(self.user)
        return engine

    def _make_feedback(self, feedback_type='LIKE'):
        fb = Mock(spec=UserFeedback)
        fb.feedback_type = feedback_type
        fb.track = self.track
        return fb

    def test_like_increments_genre(self):
        engine = self._make_engine()
        with patch('apps.core.models.RecommendationLog.objects') as mock_rl:
            mock_rl.filter.return_value.order_by.return_value.first.return_value = None
            engine.apply_feedback_learning(self._make_feedback('LIKE'))
        profile = UserProfile.objects.get(user=self.user)
        self.assertAlmostEqual(profile.data['taste_vector'].get('indie rock', 0.0), 0.1, places=4)
        self.assertAlmostEqual(profile.data['taste_vector'].get('folk', 0.0), 0.1, places=4)

    def test_dislike_decrements_genre(self):
        engine = self._make_engine()
        with patch('apps.core.models.RecommendationLog.objects') as mock_rl:
            mock_rl.filter.return_value.order_by.return_value.first.return_value = None
            engine.apply_feedback_learning(self._make_feedback('DISLIKE'))
        profile = UserProfile.objects.get(user=self.user)
        self.assertAlmostEqual(profile.data['taste_vector'].get('indie rock', 0.0), -0.1, places=4)

    def test_unlike_reverses_genre(self):
        # First apply a like
        self.profile.data['taste_vector'] = {'indie rock': 0.1, 'folk': 0.1}
        self.profile.data['preferences']['feedback_history'] = [
            {'track_id': 'tv_track_1', 'feedback_type': 'LIKE', 'track_info': {}}
        ]
        self.profile.save(update_fields=['data'])

        engine = self._make_engine()
        engine.remove_feedback_learning('tv_track_1')

        profile = UserProfile.objects.get(user=self.user)
        self.assertAlmostEqual(profile.data['taste_vector'].get('indie rock', 0.0), 0.0, places=4)
```

---

#### `backend/apps/recommendations/tests/test_bandit.py`

**Analog:** Phase 2 `backend/tests/test_scoring.py` — mock-based `unittest.TestCase` with `__new__` bypass (no DB needed for bandit sampling tests).

```python
"""Tests for Thompson Sampling bandit in HybridRecommendationEngine.get_recommendation_weights()."""
import unittest
from unittest.mock import Mock

from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine

class TestBandit(unittest.TestCase):
    """D-07, D-08: bandit state and weight sampling."""

    def _make_engine(self, source_stats=None):
        """Bypass __init__ — established pattern from Phase 2 test_scoring.py."""
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {
            'taste_vector': {},
            'preferences': {'liked_artists': [], 'disliked_artists': []},
            'base_data': {'top_artists': []},
            'source_stats': source_stats or {},
        }
        return engine

    def test_cold_start_returns_static_defaults(self):
        engine = self._make_engine(source_stats={})
        weights = engine.get_recommendation_weights()
        # With 0 observations, must use static defaults
        self.assertAlmostEqual(weights['playlist_mining'], 0.3, places=4)
        self.assertAlmostEqual(weights['artist_network'], 0.25, places=4)

    def test_cold_start_init_schema(self):
        """source_stats initialized to all-zero schema when key absent."""
        engine = self._make_engine(source_stats={})
        # After cold-start, all sources present with s=0, f=0
        weights = engine.get_recommendation_weights()
        for source in ['playlist_mining', 'artist_network', 'genre_search',
                       'related_artists', 'contextual']:
            self.assertIn(source, weights)

    def test_weights_after_cold_start_are_beta_samples(self):
        """D-08: after COLD_START_N observations, weight is sampled from Beta."""
        # Give playlist_mining 10 successes, 2 failures (well past cold-start)
        source_stats = {
            'playlist_mining': {'s': 10, 'f': 2},
            'artist_network': {'s': 0, 'f': 0},
            'genre_search': {'s': 0, 'f': 0},
            'related_artists': {'s': 0, 'f': 0},
            'contextual': {'s': 0, 'f': 0},
        }
        engine = self._make_engine(source_stats=source_stats)
        weights = engine.get_recommendation_weights()
        # Beta(11, 3) mean ~0.79 — sample must be in (0, 1)
        self.assertGreater(weights['playlist_mining'], 0.0)
        self.assertLess(weights['playlist_mining'], 1.0)
        # artist_network still cold-start → static default
        self.assertAlmostEqual(weights['artist_network'], 0.25, places=4)

    def test_all_weights_positive(self):
        """All weight values must be positive (Beta samples are always > 0)."""
        source_stats = {src: {'s': 5, 'f': 5} for src in
                        ['playlist_mining', 'artist_network', 'genre_search',
                         'related_artists', 'contextual']}
        engine = self._make_engine(source_stats=source_stats)
        weights = engine.get_recommendation_weights()
        for source, w in weights.items():
            self.assertGreater(w, 0.0, f"{source} weight must be positive")
```

---

#### `backend/apps/recommendations/tests/test_popularity_targeting.py`

**Analog:** Phase 2 `backend/tests/test_scoring.py` — mock-based `unittest.TestCase` for pure computation (no DB needed for bell-curve or midpoint math).

```python
"""Tests for bell-curve novelty and popularity midpoint update (D-10, D-11, D-12)."""
import math
import unittest
from unittest.mock import Mock

from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine

class TestBellCurveNovelty(unittest.TestCase):
    """D-10: bell-curve novelty formula."""

    def _make_engine(self, midpoint=30, width=20):
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {
            'taste_vector': {},
            'preferences': {
                'liked_artists': [], 'disliked_artists': [],
                'preferred_popularity_range': {'midpoint': midpoint, 'width': width},
            },
            'base_data': {'top_artists': []},
            'source_stats': {},
        }
        return engine

    def test_bell_curve_peaks_at_midpoint(self):
        engine = self._make_engine(midpoint=30, width=20)
        novelty = engine._bell_curve_novelty(30, 30.0, 20.0)
        self.assertAlmostEqual(novelty, 1.0, places=6,
                               msg="Novelty must be 1.0 at midpoint")

    def test_bell_curve_falls_off_symmetrically(self):
        engine = self._make_engine(midpoint=30, width=20)
        n_plus = engine._bell_curve_novelty(50, 30.0, 20.0)   # midpoint + width
        n_minus = engine._bell_curve_novelty(10, 30.0, 20.0)  # midpoint - width
        self.assertAlmostEqual(n_plus, n_minus, places=6,
                               msg="Bell curve must be symmetric around midpoint")

    def test_bell_curve_at_one_sigma_is_approx_0607(self):
        engine = self._make_engine()
        novelty = engine._bell_curve_novelty(50, 30.0, 20.0)  # 1 sigma away
        expected = math.exp(-0.5)  # ~0.6065
        self.assertAlmostEqual(novelty, expected, places=4)

    def test_score_formula_uses_bell_curve_not_linear(self):
        """D-10: _score_recommendations uses bell-curve novelty (not 1 - pop/100)."""
        engine = self._make_engine(midpoint=30, width=20)
        engine.profile.data['source_stats'] = {}
        rec = {'id': 'x', 'name': 'T', 'artist': 'A', 'album': 'B',
               'preview_url': None, 'image_url': None,
               'source': 'playlist_mining', 'score': 0.0, 'popularity': 30}
        result = engine._score_recommendations([rec])
        # novelty at pop=30 with midpoint=30 → 1.0 (peak)
        # linear would give: 1 - 30/100 = 0.70
        # bell-curve gives: 1.0
        # score = 0.4*genre_sim + 0.3*1.0 + 0.3*feedback_multiplier
        # With no taste vector and neutral artist: 0.4*0.0 + 0.3*1.0 + 0.3*1.0 = 0.60
        # (scaled by source_weight, which is static default 0.3 for playlist_mining)
        # Test that novelty component is > linear
        linear_novelty = 1 - 30 / 100.0
        self.assertGreater(result[0]['score'], 0.4 * 0 + 0.3 * linear_novelty + 0.3 * 1.0,
                           "Bell-curve at midpoint must score higher than linear novelty")


class TestPopularityMidpointUpdate(unittest.TestCase):
    """D-12: midpoint shifts toward liked track's popularity, away on dislike."""

    def test_like_shifts_midpoint_toward_track_pop(self):
        """Like with pop=60 and midpoint=30 → midpoint moves toward 60."""
        initial_midpoint = 30.0
        track_pop = 60
        lr = 0.1
        new_midpoint = initial_midpoint + lr * (track_pop - initial_midpoint)
        self.assertAlmostEqual(new_midpoint, 33.0, places=4)

    def test_dislike_shifts_midpoint_away_from_track_pop(self):
        """Dislike with pop=80 and midpoint=30 → midpoint moves away from 80."""
        initial_midpoint = 30.0
        track_pop = 80
        lr = 0.1
        signal = -1.0
        new_midpoint = initial_midpoint + lr * (track_pop - initial_midpoint) * signal
        self.assertAlmostEqual(new_midpoint, 25.0, places=4)
```

---

#### `backend/apps/core/tests/test_daily_gem_view.py`

**Analog:** Phase 2 `backend/tests/test_scoring.py` `TestRecommendationLogSource` — Django `TestCase` with DB setup + patch for external dependencies.

```python
"""Integration tests for GET /api/daily-gem/ view (D-14)."""
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import UserProfile, Track, DailyGem


class TestDailyGemView(TestCase):
    """D-14: /api/daily-gem/ returns track, explanation, and score_breakdown."""

    def setUp(self):
        self.user = User.objects.create_user('gemuser', password='pw')
        self.client.force_login(self.user)
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'data': {
                'taste_vector': {'indie rock': 5},
                'base_data': {'top_artists': []},
                'preferences': {
                    'liked_artists': [],
                    'disliked_artists': [],
                    'feedback_history': [],
                    'preferred_popularity_range': {'midpoint': 30, 'width': 20},
                },
                'source_stats': {},
            }},
        )
        self.track = Track.objects.create(
            spotify_id='gem_track_1',
            name='Gem Track',
            artist='Gem Artist',
            album='Gem Album',
            popularity=22,
            genres=['indie rock'],
        )

    def _mock_recommendations(self):
        return [{
            'id': 'gem_track_1',
            'name': 'Gem Track',
            'artist': 'Gem Artist',
            'album': 'Gem Album',
            'popularity': 22,
            'image_url': 'http://img.test',
            'preview_url': 'http://preview.test',
            'source': 'playlist_mining',
            'score': 0.85,
            '_score_breakdown': {
                'genre_sim': 0.82,
                'novelty': 0.71,
                'feedback_multiplier': 1.0,
                'top_genres': ['indie rock'],
            },
        }]

    def test_response_includes_score_breakdown(self):
        with patch(
            'apps.recommendations.hybrid_recommendation_engine.HybridRecommendationEngine.get_recommendations',
            return_value=self._mock_recommendations()
        ), patch(
            'apps.ai.ai_feedback_service.RecommendationExplainer.generate_explanation',
            return_value='This is a great hidden gem.'
        ):
            response = self.client.get('/api/daily-gem/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('score_breakdown', data)
        self.assertIn('genre_sim', data['score_breakdown'])
        self.assertIn('novelty', data['score_breakdown'])
        self.assertIn('feedback_multiplier', data['score_breakdown'])
        self.assertIn('top_genres', data['score_breakdown'])

    def test_cached_gem_returns_without_engine_call(self):
        from django.utils import timezone
        DailyGem.objects.create(
            user=self.user,
            track=self.track,
            date=timezone.localdate(),
            explanation='Cached explanation.',
            track_popularity=22,
            image_url='http://img.test',
            preview_url='http://preview.test',
        )
        with patch(
            'apps.recommendations.hybrid_recommendation_engine.HybridRecommendationEngine.get_recommendations',
        ) as mock_engine:
            response = self.client.get('/api/daily-gem/')
            mock_engine.assert_not_called()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['cached'])

    def test_force_new_bypasses_cache(self):
        from django.utils import timezone
        DailyGem.objects.create(
            user=self.user,
            track=self.track,
            date=timezone.localdate(),
            explanation='Old explanation.',
            track_popularity=22,
        )
        with patch(
            'apps.recommendations.hybrid_recommendation_engine.HybridRecommendationEngine.get_recommendations',
            return_value=self._mock_recommendations()
        ), patch(
            'apps.ai.ai_feedback_service.RecommendationExplainer.generate_explanation',
            return_value='Fresh explanation.'
        ):
            response = self.client.get('/api/daily-gem/?force_new=true')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['cached'])
        self.assertEqual(data['explanation'], 'Fresh explanation.')
```

---

## Shared Patterns

### Profile Data Mutation and Save
**Source:** `hybrid_recommendation_engine.py` `remove_feedback()` lines 881–905 (read); Phase 2 PATTERNS.md "Profile Data Access Pattern"
**Apply to:** All methods that touch `UserProfile.data` in `personalization_engine.py` and `views.py`
```python
# Always use .get() with defaults — direct key access crashes on new profiles
data = profile.data
taste_vector = data.setdefault('taste_vector', {})
prefs = data.setdefault('preferences', {})
pop_range = prefs.setdefault('preferred_popularity_range', {'midpoint': 30, 'width': 20})

# Save with update_fields to avoid overwriting concurrent changes
profile.data = data
profile.save(update_fields=['data'])
```

### OpenAI Client Init / Fallback Pattern
**Source:** `ai_feedback_service.py` `FeedbackInterpreter.__init__` + `_initialize_openai()` lines 68–86 (read)
**Apply to:** `RecommendationExplainer` class
```python
def _initialize_openai(self):
    try:
        from openai import OpenAI
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            logger.warning("OPENAI_API_KEY not set")
    except ImportError:
        logger.error("openai not installed. Run: pip install openai")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
```

### Error Handling in Engine Methods
**Source:** `hybrid_recommendation_engine.py` `_get_fallback_recommendations()` lines 789–805 (read); `remove_feedback()` lines 881–905 (read)
**Apply to:** `apply_feedback_learning()`, `remove_feedback_learning()`, `get_daily_gem()` view
```python
try:
    # ... operation
except SomeSpecificException:
    logger.warning("...")
    return  # or return default
except Exception as e:
    logger.error(f"Error in <method_name>: {str(e)}")
```

### API View Decorator Stack
**Source:** Phase 2 PATTERNS.md (views.py lines 327–336), confirmed absent in RESEARCH.md for `/api/daily-gem/`
**Apply to:** `get_daily_gem` view
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_gem(request):
    ...
```

### `__new__` Bypass for Engine Unit Tests
**Source:** Phase 2 PATTERNS.md lines 382–401 (from `test_recommendation.py` line 144)
**Apply to:** All `unittest.TestCase` tests for `HybridRecommendationEngine` (bandit, novelty)
```python
engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
engine.user = Mock(id=99)
engine.profile = Mock()
engine.profile.data = {
    'taste_vector': {},
    'base_data': {'top_artists': []},
    'preferences': {
        'liked_artists': [], 'disliked_artists': [],
        'preferred_popularity_range': {'midpoint': 30, 'width': 20},
    },
    'source_stats': {},
}
```

### Test Runner Commands
**Source:** Phase 2 PATTERNS.md lines 431–437; RESEARCH.md Validation Architecture
```bash
# Per-task (fast, single file):
cd backend && DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=$(pwd) python3 -m pytest \
  apps/recommendations/tests/test_personalization_engine.py -x -q

# Per-wave (full suite, exclude known-broken openai tests):
cd backend && DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=$(pwd) python3 -m pytest \
  tests/ apps/ -q \
  --ignore=tests/test_ai_feedback_service.py \
  --ignore=tests/test_openai_integration.py
```

---

## Known Anti-Patterns to Avoid

| Anti-Pattern | Why | What to Do Instead |
|---|---|---|
| `track_info['genres']` in `apply_feedback_learning` | `track_info` dict has only `artist`, `name`, `album` — no `genres` key (views.py line 508 confirmed by RESEARCH.md Pitfall 1) | Use `feedback.track.genres` (ORM field on `UserFeedback.track` FK) |
| `self.profile` in `PersonalizationEngine` | `PersonalizationEngine.__init__` sets only `self.user` and `self.preferences` — no `self.profile` (RESEARCH.md Pitfall 2) | `UserProfile.objects.get(user=self.user)` inside each method |
| Assuming `_score_recommendations` reads `get_recommendation_weights()` | It does NOT — only called from `get_profile_summary()` (RESEARCH.md Pitfall 3) | Add bandit weight as explicit post-score multiplier in `_score_recommendations` |
| `DailyGem.objects.create(score_breakdown=...)` | No `score_breakdown` field on `DailyGem` model (RESEARCH.md Pitfall 5) | Return in API response dict without persisting; or add field + migration |
| `PersonalizationEngine.apply_feedback_learning` calling `UserProfile.update_weights()` | `update_weights(weights)` takes 1 arg; calling it from `PersonalizationEngine` was the crash fixed in Phase 1 | Mutate `profile.data` directly; call `profile.save(update_fields=['data'])` |

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `backend/apps/recommendations/`, `backend/apps/core/`, `backend/apps/ai/`, `.planning/phases/02-user-taste-vector-real-scoring/02-PATTERNS.md`
**Files read:** `personalization_engine.py` (full, 306 lines), `hybrid_recommendation_engine.py` (lines 1–100, 750–950), `ai_feedback_service.py` (full, 208 lines), `03-CONTEXT.md` (full), `03-RESEARCH.md` (full), `02-PATTERNS.md` (full)
**Note:** `backend/apps/core/models.py` and `backend/apps/core/views.py` were inaccessible via filesystem (EPERM mid-session). All model/view citations are sourced from RESEARCH.md (verified HIGH confidence — direct codebase inspection in prior session) and Phase 2 PATTERNS.md.
**Pattern extraction date:** 2026-05-11

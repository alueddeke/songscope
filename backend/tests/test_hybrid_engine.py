"""
HybridRecommendationEngine coverage — cold-start and fallback paths.

Covers three HIGH/MEDIUM gaps from the backend audit:
  1. Cold-start user (no top_artists, no source_stats) — engine returns weights without crash
  2. _get_fallback_recommendations when Spotify client unavailable → returns []
  3. _score_recommendations on empty input → returns []
"""
import unittest
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase

from apps.recommendations.hybrid_recommendation_engine import (
    HybridRecommendationEngine,
    SOURCE_DEFAULTS,
    COLD_START_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cold_start_engine():
    """Engine with empty profile — simulates a brand-new user."""
    engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
    engine.user = Mock(id=1)
    engine.profile = Mock()
    engine.profile.data = {
        'taste_vector': {},
        'base_data': {'top_artists': []},
        'preferences': {
            'liked_artists': [],
            'disliked_artists': [],
        },
        'source_stats': {},
    }
    engine.profile.get_recommendation_weights.return_value = {}
    return engine


def _make_rec(track_id='trk1', popularity=50, source='artist_network'):
    return {
        'id': track_id,
        'name': 'Test Track',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'preview_url': None,
        'image_url': None,
        'source': source,
        'score': 0.0,
        'popularity': popularity,
    }


# ---------------------------------------------------------------------------
# 1. Cold-start: empty source_stats → neutral weights, no crash
# ---------------------------------------------------------------------------

class TestColdStartWeights(unittest.TestCase):
    """
    Regression: get_recommendation_weights() must not crash or return empty when
    source_stats is absent. It should return neutral 1.0 weights for all sources
    plus the bandit_active sentinel.
    """

    def test_empty_source_stats_returns_neutral_weights(self):
        engine = make_cold_start_engine()
        weights = engine.get_recommendation_weights()

        # bandit_active must be set so callers know Phase 3 is wired
        self.assertIn('bandit_active', weights)
        self.assertTrue(weights['bandit_active'])

        # All 5 canonical sources must appear
        for source in SOURCE_DEFAULTS:
            self.assertIn(
                source, weights,
                msg=f"Cold-start weights missing source '{source}'",
            )

    def test_empty_source_stats_weights_are_neutral(self):
        """With no stats, each source should get weight 1.0 (no penalty)."""
        engine = make_cold_start_engine()
        weights = engine.get_recommendation_weights()

        for source in SOURCE_DEFAULTS:
            self.assertEqual(
                weights[source],
                1.0,
                msg=(
                    f"Cold-start source '{source}' should get weight 1.0 "
                    f"(no data = no penalty). Got {weights[source]}."
                ),
            )

    def test_cold_start_score_recommendations_does_not_crash(self):
        """_score_recommendations must return a list and not raise on cold-start profile."""
        engine = make_cold_start_engine()
        recs = [_make_rec('t1', 30), _make_rec('t2', 60), _make_rec('t3', 90)]
        scored = engine._score_recommendations(recs)

        self.assertIsInstance(scored, list)
        self.assertEqual(len(scored), 3)
        for rec in scored:
            self.assertIn('score', rec)
            self.assertIsInstance(rec['score'], float)


# ---------------------------------------------------------------------------
# 2. _score_recommendations on empty input
# ---------------------------------------------------------------------------

class TestScoreRecommendationsEdgeCases(unittest.TestCase):

    def test_empty_input_returns_empty_list(self):
        """_score_recommendations([]) must return [] not raise."""
        engine = make_cold_start_engine()
        result = engine._score_recommendations([])
        self.assertEqual(result, [])

    def test_single_track_is_scored(self):
        """Single-track input is handled without index errors."""
        engine = make_cold_start_engine()
        rec = _make_rec('only_track', 40)
        result = engine._score_recommendations([rec])
        self.assertEqual(len(result), 1)
        self.assertIn('score', result[0])


# ---------------------------------------------------------------------------
# 3. _get_fallback_recommendations when Spotify client unavailable
# ---------------------------------------------------------------------------

class TestFallbackRecommendations(unittest.TestCase):
    """
    When no Spotify client is available (token missing/expired, no network),
    the fallback must return [] rather than raising.
    """

    def test_no_spotify_client_returns_empty(self):
        engine = make_cold_start_engine()

        with patch.object(engine, '_get_spotify_client', return_value=None):
            result = engine._get_fallback_recommendations(limit=5)

        self.assertEqual(
            result,
            [],
            msg="_get_fallback_recommendations must return [] when Spotify client is None",
        )

    def test_discovery_engine_exception_returns_empty(self):
        """If TrackDiscoveryEngine raises, fallback catches it and returns []."""
        engine = make_cold_start_engine()
        mock_sp = MagicMock()

        with patch.object(engine, '_get_spotify_client', return_value=mock_sp):
            with patch(
                'apps.recommendations.hybrid_recommendation_engine.TrackDiscoveryEngine'
            ) as mock_discovery_cls:
                mock_discovery_cls.return_value.get_personalized_recommendations.side_effect = (
                    Exception("Spotify 503")
                )
                result = engine._get_fallback_recommendations(limit=5)

        self.assertEqual(result, [])

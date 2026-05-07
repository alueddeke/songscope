"""
Phase 2 tests: taste vector, cosine similarity, score formula, dead code removal,
and RecommendationLog.source field.
"""
import unittest
from unittest.mock import Mock

from django.test import TestCase
from django.contrib.auth.models import User

from apps.core.models import RecommendationLog, Track, UserProfile
from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine


# ---------------------------------------------------------------------------
# Helper: bypass HybridRecommendationEngine.__init__ (no DB / no Spotify needed)
# Pattern from test_recommendation.py line 144.
# ---------------------------------------------------------------------------

def make_engine(taste_vector=None, liked_artists=None, disliked_artists=None, top_artists=None):
    engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
    engine.user = Mock(id=99)
    engine.profile = Mock()
    engine.profile.data = {
        'taste_vector': taste_vector or {},
        'base_data': {'top_artists': top_artists or []},
        'preferences': {
            'liked_artists': liked_artists or [],
            'disliked_artists': disliked_artists or [],
        },
    }
    return engine


def _make_rec(artist='Unknown Artist', popularity=50, source='artist_network'):
    return {
        'id': 'track_x',
        'name': 'Test Track',
        'artist': artist,
        'album': 'Test Album',
        'preview_url': None,
        'image_url': None,
        'source': source,
        'score': 0.0,
        'popularity': popularity,
    }


# ---------------------------------------------------------------------------
# Taste vector build tests (D-01, D-02, D-03, D-04)
# ---------------------------------------------------------------------------

class TestBuildTasteVector(unittest.TestCase):

    def test_builds_genre_counts_from_top_artists(self):
        engine = make_engine()
        top_artists = [
            {'name': 'Artist A', 'genres': ['indie rock', 'folk']},
            {'name': 'Artist B', 'genres': ['indie rock', 'pop']},
        ]
        engine.profile.data['base_data']['top_artists'] = top_artists
        engine._build_taste_vector()
        tv = engine.profile.data['taste_vector']
        self.assertEqual(tv['indie rock'], 2)
        self.assertEqual(tv['folk'], 1)
        self.assertEqual(tv['pop'], 1)

    def test_empty_top_artists_produces_empty_vector(self):
        engine = make_engine()
        engine.profile.data['base_data']['top_artists'] = []
        engine._build_taste_vector()
        self.assertEqual(engine.profile.data['taste_vector'], {})

    def test_artist_with_no_genres_skipped(self):
        engine = make_engine()
        top_artists = [
            {'name': 'Artist A', 'genres': []},
            {'name': 'Artist B', 'genres': ['ambient']},
        ]
        engine.profile.data['base_data']['top_artists'] = top_artists
        engine._build_taste_vector()
        tv = engine.profile.data['taste_vector']
        self.assertEqual(tv, {'ambient': 1})

    def test_missing_base_data_produces_empty_vector(self):
        engine = make_engine()
        engine.profile.data = {}  # simulate brand-new profile
        engine._build_taste_vector()
        self.assertEqual(engine.profile.data.get('taste_vector', {}), {})


# ---------------------------------------------------------------------------
# Cosine similarity helper tests (D-05, D-06)
# ---------------------------------------------------------------------------

class TestCosineSimilarity(unittest.TestCase):

    def setUp(self):
        self.engine = make_engine()

    def test_identical_vectors_return_one(self):
        vec = {'indie rock': 5, 'folk': 3}
        self.assertAlmostEqual(self.engine._cosine_similarity(vec, vec), 1.0, places=5)

    def test_orthogonal_vectors_return_zero(self):
        vec_a = {'indie rock': 5}
        vec_b = {'pop': 3}
        self.assertAlmostEqual(self.engine._cosine_similarity(vec_a, vec_b), 0.0, places=5)

    def test_empty_vec_a_returns_zero(self):
        self.assertEqual(self.engine._cosine_similarity({}, {'folk': 1}), 0.0)

    def test_empty_vec_b_returns_zero(self):
        self.assertEqual(self.engine._cosine_similarity({'folk': 1}, {}), 0.0)

    def test_partial_overlap_between_zero_and_one(self):
        vec_a = {'indie rock': 3, 'folk': 2}
        vec_b = {'indie rock': 1}
        sim = self.engine._cosine_similarity(vec_a, vec_b)
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)


# ---------------------------------------------------------------------------
# Score formula tests (D-05, D-06, D-07, D-08 — LOCKED formula)
# ---------------------------------------------------------------------------

class TestScoreFormula(unittest.TestCase):

    def test_locked_formula_weights(self):
        """score = 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier (LOCKED)"""
        # popularity=0 → novelty=1.0; neutral artist; exact genre match → genre_sim=1.0
        engine = make_engine(
            taste_vector={'indie rock': 5},
            top_artists=[{'name': 'Band A', 'genres': ['indie rock']}],
        )
        recs = [_make_rec(artist='Band A', popularity=0)]
        result = engine._score_recommendations(recs)
        # genre_sim=1.0, novelty=1.0, feedback_multiplier=1.0 (neutral)
        # score = 0.4*1.0 + 0.3*1.0 + 0.3*1.0 = 1.0
        self.assertAlmostEqual(result[0]['score'], 1.0, places=4)

    def test_unknown_artist_genre_sim_is_zero(self):
        """D-06: artist not in top_artists → genre_sim=0.0"""
        engine = make_engine(taste_vector={'indie rock': 5})
        recs = [_make_rec(artist='Unknown Artist', popularity=50)]
        result = engine._score_recommendations(recs)
        # genre_sim=0.0, novelty=0.5, feedback_multiplier=1.0
        # score = 0.0 + 0.3*0.5 + 0.3*1.0 = 0.15 + 0.30 = 0.45
        self.assertAlmostEqual(result[0]['score'], 0.45, places=4)

    def test_liked_artist_boosts_feedback_multiplier(self):
        """liked artist → feedback_multiplier=1.5"""
        engine = make_engine(
            taste_vector={},
            liked_artists=['Great Band'],
        )
        recs = [_make_rec(artist='Great Band', popularity=100)]
        result = engine._score_recommendations(recs)
        # genre_sim=0.0, novelty=0.0, feedback_multiplier=1.5
        # score = 0.0 + 0.0 + 0.3*1.5 = 0.45
        self.assertAlmostEqual(result[0]['score'], 0.45, places=4)

    def test_disliked_artist_reduces_feedback_multiplier(self):
        """disliked artist → feedback_multiplier=0.5"""
        engine = make_engine(
            taste_vector={},
            disliked_artists=['Bad Band'],
        )
        recs = [_make_rec(artist='Bad Band', popularity=0)]
        result = engine._score_recommendations(recs)
        # genre_sim=0.0, novelty=1.0, feedback_multiplier=0.5
        # score = 0.0 + 0.3*1.0 + 0.3*0.5 = 0.30 + 0.15 = 0.45
        self.assertAlmostEqual(result[0]['score'], 0.45, places=4)

    def test_results_sorted_descending(self):
        """Higher-scoring rec appears first"""
        engine = make_engine(
            taste_vector={'indie rock': 5},
            top_artists=[
                {'name': 'High Score Band', 'genres': ['indie rock']},
                {'name': 'Low Score Band', 'genres': []},
            ],
        )
        recs = [
            _make_rec(artist='Low Score Band', popularity=99),   # low genre_sim, low novelty
            _make_rec(artist='High Score Band', popularity=0),   # high genre_sim, high novelty
        ]
        result = engine._score_recommendations(recs)
        self.assertGreater(result[0]['score'], result[1]['score'])

    def test_safe_get_on_empty_profile(self):
        """No KeyError on brand-new profile with no preferences or taste_vector"""
        engine = make_engine()
        engine.profile.data = {}  # completely empty
        recs = [_make_rec()]
        # Should not raise; score should be a valid float
        result = engine._score_recommendations(recs)
        self.assertIsInstance(result[0]['score'], float)


# ---------------------------------------------------------------------------
# Dead code removal test (D-08, D-09)
# ---------------------------------------------------------------------------

class TestDeadCodeRemoved(unittest.TestCase):

    def test_update_weights_from_ai_feedback_deleted(self):
        self.assertFalse(
            hasattr(HybridRecommendationEngine, '_update_weights_from_ai_feedback'),
            "_update_weights_from_ai_feedback should have been deleted in Phase 2"
        )

    def test_add_ai_feedback_still_exists(self):
        self.assertTrue(
            hasattr(HybridRecommendationEngine, 'add_ai_feedback'),
            "add_ai_feedback() must still exist after dead code removal"
        )


# ---------------------------------------------------------------------------
# RecommendationLog.source field tests (D-10, D-11)
# ---------------------------------------------------------------------------

class TestRecommendationLogSource(TestCase):

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

    def test_source_field_exists(self):
        self.assertTrue(hasattr(RecommendationLog, 'source'))

    def test_log_recommendation_stores_source(self):
        RecommendationLog.log_recommendation(self.user, self.track, source='playlist_mining')
        log = RecommendationLog.objects.get(user=self.user, track=self.track)
        self.assertEqual(log.source, 'playlist_mining')

    def test_log_recommendation_default_source_is_empty(self):
        RecommendationLog.log_recommendation(self.user, self.track)
        log = RecommendationLog.objects.get(user=self.user, track=self.track)
        self.assertEqual(log.source, '')

    def test_no_win_rate_logic_in_phase2(self):
        """D-11: win-rate query logic is Phase 3 scope only"""
        import inspect
        src = inspect.getsource(RecommendationLog)
        self.assertNotIn('win_rate', src)
        self.assertNotIn('strategy_stats', src)

"""
Unit tests for hybrid_recommendation_engine fixes.
Phase 1: Bug 5 (top-artist filter), Bug 6 (DB-backed exclusion set), Bug 7 (artist_related_artists strategy).
Stubs created in Plan 01 — Plan 03 implements the methods these tests verify.
"""
import unittest
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import DailyGem, RecommendationLog, Track, UserProfile


class TestPersistentExclusionSet(TestCase):
    """Bug 6: _get_persistent_exclusion_set returns DB-backed set of seen track IDs."""

    def setUp(self):
        self.user = User.objects.create_user('exuser', password='pw')
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'data': {'base_data': {'top_artists': []}, 'preferences': {}}},
        )
        self.logged_track = Track.objects.create(
            spotify_id='excl_track_logged',
            name='Logged Gem',
            artist='Artist',
            album='Album',
        )
        RecommendationLog.objects.create(user=self.user, track=self.logged_track)

    def test_logged_track_in_exclusion_set(self):
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertIn('excl_track_logged', exclusion)

    def test_dailygem_track_in_exclusion_set(self):
        from datetime import date
        gem_track = Track.objects.create(
            spotify_id='excl_track_gem',
            name='Gem',
            artist='Artist',
            album='Album',
        )
        DailyGem.objects.create(user=self.user, date=date.today(), track=gem_track)
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertIn('excl_track_gem', exclusion)

    def test_error_sentinel_excluded(self):
        """'error_log' sentinel track must not appear in exclusion set."""
        err_track = Track.objects.create(
            spotify_id='error_log',
            name='Error Log',
            artist='System',
            album='Error',
        )
        RecommendationLog.objects.create(user=self.user, track=err_track)
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertNotIn('error_log', exclusion)

    def test_exclusion_set_returns_python_set(self):
        """Must return Python set (not QuerySet) so `in` checks are O(1)."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        exclusion = engine._get_persistent_exclusion_set()
        self.assertIsInstance(exclusion, set)


class TestFilterOutLikedSongs(TestCase):
    """Bug 5: _filter_out_liked_songs must NOT filter by artist name (top_artists block removed)."""

    def setUp(self):
        self.user = User.objects.create_user('filtuser', password='pw')
        # Profile with a top artist named 'Top Artist' — the bug would filter ALL their tracks.
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'data': {
                    'base_data': {
                        'top_artists': [{'id': 'art1', 'name': 'Top Artist'}]
                    },
                    'preferences': {},
                }
            },
        )

    def test_track_by_top_artist_not_filtered(self):
        """A previously-unseen track by a top artist must pass through (Bug 5 fix)."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        recs = [
            {'id': 'new_deep_cut_1', 'name': 'Deep Cut', 'artist': 'Top Artist',
             'album': 'B-Sides', 'preview_url': None, 'image_url': None,
             'source': 'test', 'score': 0.0, 'popularity': 20},
        ]
        filtered = engine._filter_out_liked_songs(recs)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 'new_deep_cut_1')

    def test_previously_logged_track_is_filtered(self):
        """A track already in RecommendationLog must be filtered out (Bug 6 path)."""
        track = Track.objects.create(
            spotify_id='already_seen',
            name='Already Seen',
            artist='Some Artist',
            album='Album',
        )
        RecommendationLog.objects.create(user=self.user, track=track)
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine(self.user)
        recs = [
            {'id': 'already_seen', 'name': 'Already Seen', 'artist': 'Some Artist',
             'album': 'Album', 'preview_url': None, 'image_url': None,
             'source': 'test', 'score': 0.0, 'popularity': 20},
            {'id': 'new_track', 'name': 'New Track', 'artist': 'Some Artist',
             'album': 'Album', 'preview_url': None, 'image_url': None,
             'source': 'test', 'score': 0.0, 'popularity': 20},
        ]
        filtered = engine._filter_out_liked_songs(recs)
        ids = [r['id'] for r in filtered]
        self.assertNotIn('already_seen', ids)
        self.assertIn('new_track', ids)


class TestRelatedArtistStrategy(unittest.TestCase):
    """Bug 7: _get_related_artist_recommendations is the 5th candidate strategy."""

    def test_method_exists_on_engine(self):
        """The new method must be present on HybridRecommendationEngine."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        self.assertTrue(
            hasattr(HybridRecommendationEngine, '_get_related_artist_recommendations'),
            "HybridRecommendationEngine must define _get_related_artist_recommendations (Bug 7)",
        )

    def test_returns_candidates_on_valid_api_response(self):
        """When spotipy returns data, the method yields candidates with source='related_artists'."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {
            'base_data': {'top_artists': [{'id': 'art1', 'name': 'Top Artist'}]},
            'preferences': {'liked_artists': [], 'disliked_artists': []},
        }

        mock_sp = Mock()
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

        with patch.object(engine, '_get_spotify_client', return_value=mock_sp), \
             patch.object(engine, '_check_rate_limit', return_value=True):
            results = engine._get_related_artist_recommendations(limit=5)

        self.assertGreater(len(results), 0, "Strategy must return non-empty candidates")
        self.assertEqual(results[0]['source'], 'related_artists')

    def test_returns_empty_list_when_client_unavailable(self):
        """When _get_spotify_client returns None, method returns []."""
        from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        engine.profile.data = {'base_data': {'top_artists': []}, 'preferences': {}}
        with patch.object(engine, '_get_spotify_client', return_value=None):
            results = engine._get_related_artist_recommendations(limit=5)
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()

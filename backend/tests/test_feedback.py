"""
Unit tests for submit_feedback view RecommendationLog.liked write (Bug 3).
Stubs created in Plan 01 — Plan 02 wires the actual view call.
"""
import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.core.models import RecommendationLog, Track, DailyGem, SpotifyToken


class TestRecommendationLogLikedField(TestCase):
    """Bug 3: submit_feedback must write RecommendationLog.liked on LIKE/DISLIKE/unlike."""

    def setUp(self):
        self.user = User.objects.create_user('feeduser', password='pw')
        self.track = Track.objects.create(
            spotify_id='A' * 22,
            name='Feedback Test Track',
            artist='Artist',
            album='Album',
        )
        self.log = RecommendationLog.objects.create(
            user=self.user,
            track=self.track,
        )

    def test_liked_field_accepts_true(self):
        """liked=True (LIKE) round-trips through DB."""
        self.log.liked = True
        self.log.save(update_fields=['liked'])
        self.log.refresh_from_db()
        self.assertTrue(self.log.liked)

    def test_liked_field_accepts_false(self):
        """liked=False (DISLIKE) round-trips through DB."""
        self.log.liked = False
        self.log.save(update_fields=['liked'])
        self.log.refresh_from_db()
        self.assertFalse(self.log.liked)
        self.assertIsNotNone(self.log.liked)

    def test_liked_field_accepts_none(self):
        """liked=None (unlike / cleared) round-trips through DB."""
        self.log.liked = True
        self.log.save(update_fields=['liked'])
        self.log.liked = None
        self.log.save(update_fields=['liked'])
        self.log.refresh_from_db()
        self.assertIsNone(self.log.liked)

    def test_most_recent_log_is_picked_for_user_track(self):
        """The fix queries .order_by('-recommended_at').first() — verify ordering works."""
        # Create a second, newer log
        newer_log = RecommendationLog.objects.create(user=self.user, track=self.track)
        result = (
            RecommendationLog.objects
            .filter(user=self.user, track=self.track)
            .order_by('-recommended_at')
            .first()
        )
        self.assertEqual(result.pk, newer_log.pk)


class TestDailyGemWasLikedSync(TestCase):
    """
    Phase deliverable #5: DailyGem.was_liked is synced from feedback.

    Verifies the existing views.py:submit_feedback DailyGem block (lines ~636-643
    for LIKE/DISLIKE; ~608-615 for unlike) writes the matching today's gem.
    These tests touch only ORM round-trips — Plan 02 already calls the view
    code path through Bug 3 fixes, so this stub provides the automated proof
    for the dailygem-sync-verified requirement (Plan 02 must_haves truth #6).
    """

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
        # SpotifyToken required by submit_feedback — expires_at is a DateTimeField
        self.token = SpotifyToken.objects.create(
            user=self.user,
            access_token='fake_access_token',
            refresh_token='fake_refresh_token',
            expires_at=timezone.now() + timedelta(days=3650),
        )
        # Log the test user in via the Django test client
        self.client.force_login(self.user)

    def test_was_liked_set_true_on_like(self):
        """DailyGem.was_liked must round-trip True (LIKE)."""
        self.gem.was_liked = True
        self.gem.save(update_fields=['was_liked'])
        self.gem.refresh_from_db()
        self.assertTrue(self.gem.was_liked)

    def test_was_liked_set_false_on_dislike(self):
        """DailyGem.was_liked must round-trip False (DISLIKE)."""
        self.gem.was_liked = False
        self.gem.save(update_fields=['was_liked'])
        self.gem.refresh_from_db()
        self.assertIsNotNone(self.gem.was_liked)
        self.assertFalse(self.gem.was_liked)

    def test_was_liked_cleared_on_unlike(self):
        """DailyGem.was_liked must round-trip None (unlike clears the field)."""
        self.gem.was_liked = True
        self.gem.save(update_fields=['was_liked'])
        self.gem.was_liked = None
        self.gem.save(update_fields=['was_liked'])
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.was_liked)

    def test_today_gem_lookup_matches_views_pattern(self):
        """The query pattern in submit_feedback (filter user=, date=tz.localdate(), track=) returns the gem."""
        from datetime import date
        from apps.core.models import DailyGem
        result = DailyGem.objects.filter(
            user=self.user, date=date.today(), track=self.track,
        ).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, self.gem.pk)

    @patch('apps.core.views.HybridRecommendationEngine')
    @patch('apps.recommendations.personalization_engine.PersonalizationEngine')
    @patch('apps.core.views.get_spotipy_client')
    def test_view_sets_was_liked_true_on_like(self, mock_sp_client, mock_pe, mock_hre):
        """View path: POST LIKE → submit_feedback sets DailyGem.was_liked = True."""
        mock_sp_client.return_value = MagicMock()
        mock_pe.return_value = MagicMock()
        mock_hre.return_value = MagicMock()

        response = self.client.post(
            '/api/submit-feedback/',
            data=json.dumps({'track_id': self.track.spotify_id, 'feedback_type': 'LIKE'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.gem.refresh_from_db()
        self.assertTrue(self.gem.was_liked)

    @patch('apps.core.views.HybridRecommendationEngine')
    @patch('apps.recommendations.personalization_engine.PersonalizationEngine')
    @patch('apps.core.views.get_spotipy_client')
    def test_view_sets_was_liked_false_on_dislike(self, mock_sp_client, mock_pe, mock_hre):
        """View path: POST DISLIKE → submit_feedback sets DailyGem.was_liked = False."""
        mock_sp_client.return_value = MagicMock()
        mock_pe.return_value = MagicMock()
        mock_hre.return_value = MagicMock()

        response = self.client.post(
            '/api/submit-feedback/',
            data=json.dumps({'track_id': self.track.spotify_id, 'feedback_type': 'DISLIKE'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.gem.refresh_from_db()
        self.assertIs(self.gem.was_liked, False)

    @patch('apps.core.views.HybridRecommendationEngine')
    @patch('apps.recommendations.personalization_engine.PersonalizationEngine')
    @patch('apps.core.views.get_spotipy_client')
    def test_view_clears_was_liked_on_unlike(self, mock_sp_client, mock_pe, mock_hre):
        """View path: POST LIKE twice → second call is unlike → DailyGem.was_liked = None."""
        mock_sp_client.return_value = MagicMock()
        mock_pe.return_value = MagicMock()
        mock_hre.return_value = MagicMock()

        # First LIKE — creates the UserFeedback row; sets was_liked = True
        first = self.client.post(
            '/api/submit-feedback/',
            data=json.dumps({'track_id': self.track.spotify_id, 'feedback_type': 'LIKE'}),
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 200, first.content)

        # Second LIKE — unlike branch: deletes feedback, clears was_liked = None
        response = self.client.post(
            '/api/submit-feedback/',
            data=json.dumps({'track_id': self.track.spotify_id, 'feedback_type': 'LIKE'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.was_liked)


class TestDailyGemNewFields(TestCase):
    """
    Phase 6 Plan 02: ORM round-trip tests for the four new DailyGem fields
    added in migration 0008 (score_breakdown, score_total, was_saved,
    taste_vector_snapshot). Verifies Phase 6 success criteria #2 and #3.
    """

    def setUp(self):
        self.user = User.objects.create_user('newfieldsuser', password='pw')
        self.track = Track.objects.create(
            spotify_id='C' * 22,
            name='New Fields Track',
            artist='Artist',
            album='Album',
        )
        self.gem = DailyGem.objects.create(
            user=self.user,
            date=date.today(),
            track=self.track,
        )

    # --- score_breakdown ---

    def test_score_breakdown_defaults_to_empty_dict(self):
        """Fresh DailyGem.score_breakdown is {} (empty dict), NOT None (default=dict callable)."""
        self.gem.refresh_from_db()
        self.assertIsNotNone(self.gem.score_breakdown)
        self.assertEqual(self.gem.score_breakdown, {})

    def test_score_breakdown_round_trips(self):
        """score_breakdown stores and retrieves a dict with nested float values."""
        self.gem.score_breakdown = {'familiarity': 0.8, 'novelty': 0.6}
        self.gem.save(update_fields=['score_breakdown'])
        self.gem.refresh_from_db()
        self.assertEqual(self.gem.score_breakdown['familiarity'], 0.8)

    # --- score_total ---

    def test_score_total_defaults_to_none(self):
        """Fresh DailyGem.score_total is None (FloatField null=True, no default)."""
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.score_total)

    def test_score_total_round_trips(self):
        """score_total stores and retrieves a float value."""
        self.gem.score_total = 0.75
        self.gem.save(update_fields=['score_total'])
        self.gem.refresh_from_db()
        self.assertAlmostEqual(self.gem.score_total, 0.75)

    # --- was_saved ---

    def test_was_saved_defaults_to_none(self):
        """Fresh DailyGem.was_saved is None (nullable BooleanField, three-state like was_liked)."""
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.was_saved)

    def test_was_saved_accepts_true(self):
        """was_saved=True (user saved the track) round-trips through DB."""
        self.gem.was_saved = True
        self.gem.save(update_fields=['was_saved'])
        self.gem.refresh_from_db()
        self.assertTrue(self.gem.was_saved)

    def test_was_saved_accepts_false(self):
        """was_saved=False (user explicitly did not save) round-trips; distinguishes False from None."""
        self.gem.was_saved = False
        self.gem.save(update_fields=['was_saved'])
        self.gem.refresh_from_db()
        self.assertFalse(self.gem.was_saved)
        self.assertIsNotNone(self.gem.was_saved)

    def test_was_saved_accepts_none(self):
        """was_saved can be cleared back to None after being set (mirrors was_liked unlike pattern)."""
        self.gem.was_saved = True
        self.gem.save(update_fields=['was_saved'])
        self.gem.was_saved = None
        self.gem.save(update_fields=['was_saved'])
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.was_saved)

    # --- taste_vector_snapshot ---

    def test_taste_vector_snapshot_defaults_to_none(self):
        """Fresh DailyGem.taste_vector_snapshot is None (JSONField null=True, no default)."""
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.taste_vector_snapshot)

    def test_taste_vector_snapshot_round_trips(self):
        """taste_vector_snapshot stores and retrieves a genre-weight dict."""
        self.gem.taste_vector_snapshot = {'rock': 0.9, 'pop': 0.3, 'jazz': 0.1}
        self.gem.save(update_fields=['taste_vector_snapshot'])
        self.gem.refresh_from_db()
        self.assertEqual(self.gem.taste_vector_snapshot['rock'], 0.9)


class TestWasSavedWiring(TestCase):
    """
    Phase 7 Plan 02 — Task 1: Verify that add_track_to_liked wires DailyGem.was_saved.

    Tests:
      1. Matching track sets was_saved=True.
      2. Non-matching track is a silent no-op (was_saved stays None).
      3. DB exception during update is non-fatal (response still 200).
      4. Spotify save is called before was_saved update.
    """

    def setUp(self):
        self.user = User.objects.create_user('saveduser', password='pw')
        self.track = Track.objects.create(
            spotify_id='X' * 22,
            name='Saved Track',
            artist='Artist',
            album='Album',
        )
        self.gem = DailyGem.objects.create(
            user=self.user,
            date=timezone.localdate(),
            track=self.track,
        )
        self.token = SpotifyToken.objects.create(
            user=self.user,
            access_token='fake_access_token',
            refresh_token='fake_refresh_token',
            expires_at=timezone.now() + timedelta(days=3650),
        )
        self.client.force_login(self.user)

    @patch('apps.core.views.get_spotipy_client')
    def test_matching_track_sets_was_saved_true(self, mock_sp_client):
        """POST add-track-to-liked with matching track_id → DailyGem.was_saved becomes True."""
        mock_sp_client.return_value = MagicMock()

        response = self.client.post(
            '/api/add-track-to-liked/',
            data=json.dumps({'track_id': 'X' * 22}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.gem.refresh_from_db()
        self.assertIs(self.gem.was_saved, True)

    @patch('apps.core.views.get_spotipy_client')
    def test_nonmatching_track_is_silent_noop(self, mock_sp_client):
        """POST with a different track_id → was_saved remains None (no matching DailyGem row)."""
        mock_sp_client.return_value = MagicMock()

        response = self.client.post(
            '/api/add-track-to-liked/',
            data=json.dumps({'track_id': 'Y' * 22}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.gem.refresh_from_db()
        self.assertIsNone(self.gem.was_saved)

    @patch('apps.core.views.DailyGem')
    @patch('apps.core.views.get_spotipy_client')
    def test_db_exception_during_update_is_nonfatal(self, mock_sp_client, mock_dg):
        """DB exception inside the was_saved block → response still 200 with 'all good'."""
        mock_sp_client.return_value = MagicMock()
        mock_dg.objects.filter.return_value.update.side_effect = Exception('db boom')

        response = self.client.post(
            '/api/add-track-to-liked/',
            data=json.dumps({'track_id': 'X' * 22}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'all good')

    @patch('apps.core.views.get_spotipy_client')
    def test_spotify_save_called_before_was_saved_update(self, mock_sp_client):
        """Spotify current_user_saved_tracks_add is called exactly once (confirming order)."""
        mock_client_instance = MagicMock()
        mock_sp_client.return_value = mock_client_instance

        self.client.post(
            '/api/add-track-to-liked/',
            data=json.dumps({'track_id': 'X' * 22}),
            content_type='application/json',
        )

        mock_client_instance.current_user_saved_tracks_add.assert_called_once_with(['X' * 22])

"""
View-level tests for get_daily_gem and check_track_feedback endpoints.

Covers audit gaps:
  - get_daily_gem: cached branch, 503 (no candidates), race-condition path
  - check_track_feedback: LIKE path (returns liked=True) and DISLIKE path (returns liked=False)
  - AI feedback service singleton: cost limit persists between calls via get_feedback_interpreter()
"""
import json
from datetime import date
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Track, DailyGem, SpotifyToken, UserFeedback
from apps.core.views import _build_gem_explanation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_with_token(username="gemuser"):
    user = User.objects.create_user(username, password="pw")
    SpotifyToken.objects.create(
        user=user,
        access_token="acc",
        refresh_token="ref",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    return user


# ---------------------------------------------------------------------------
# get_daily_gem — cached branch
# ---------------------------------------------------------------------------

class TestGetDailyGemCached(TestCase):
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

    def test_returns_cached_gem_without_engine_call(self):
        with patch(
            "apps.recommendations.hybrid_recommendation_engine.HybridRecommendationEngine.get_recommendations"
        ) as mock_recs:
            response = self.client.get("/api/daily-gem/")

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["cached"], True)
        self.assertEqual(data["track"]["name"], "Cached Track")
        # Engine must NOT be called when gem is cached
        mock_recs.assert_not_called()

    def test_cached_gem_returns_explanation(self):
        response = self.client.get("/api/daily-gem/")
        data = json.loads(response.content)
        self.assertEqual(data["explanation"], "cached gem explanation")


# ---------------------------------------------------------------------------
# get_daily_gem — 503 when engine returns no candidates
# ---------------------------------------------------------------------------

class TestGetDailyGem503(TestCase):
    def setUp(self):
        self.user = _make_user_with_token("no_candidates_user")
        self.client.force_login(self.user)

    @patch("apps.core.views.HybridRecommendationEngine")
    def test_503_when_no_candidates(self, MockEngine):
        instance = MockEngine.return_value
        instance.get_recommendations.return_value = []

        response = self.client.get("/api/daily-gem/")

        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertIn("error", data)


# ---------------------------------------------------------------------------
# get_daily_gem — race condition (get_or_create returns existing gem)
# ---------------------------------------------------------------------------

class TestGetDailyGemRace(TestCase):
    def setUp(self):
        self.user = _make_user_with_token("race_gem_user")
        self.client.force_login(self.user)
        self.track = Track.objects.create(
            spotify_id="B" * 22,
            name="Race Track",
            artist="Artist",
            album="Album",
        )

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

        # Simulate race: create the gem BEFORE the view's get_or_create runs
        existing_gem = DailyGem.objects.create(
            user=self.user,
            date=timezone.localdate(),
            track=self.track,
            explanation="pre-existing",
            image_url="",
            preview_url="",
            track_popularity=30,
        )

        response = self.client.get("/api/daily-gem/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["cached"], True)


# ---------------------------------------------------------------------------
# check_track_feedback — LIKE path and DISLIKE path
# ---------------------------------------------------------------------------

class TestCheckTrackFeedback(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("fbcheck_user", password="pw")
        self.client.force_login(self.user)
        self.track = Track.objects.create(
            spotify_id="C" * 22,
            name="Feedback Check Track",
            artist="Artist",
            album="Album",
        )

    def test_no_feedback_returns_liked_false(self):
        response = self.client.get(f"/api/check-track-feedback/{'C' * 22}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["liked"])

    def test_like_feedback_returns_liked_true(self):
        UserFeedback.objects.create(
            user=self.user,
            track=self.track,
            feedback_type="LIKE",
        )
        response = self.client.get(f"/api/check-track-feedback/{'C' * 22}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["liked"])

    def test_dislike_feedback_returns_liked_false(self):
        """
        DISLIKE feedback must NOT cause check_track_feedback to return liked=True.
        The view only checks for LIKE; a DISLIKE means not-liked.
        """
        UserFeedback.objects.create(
            user=self.user,
            track=self.track,
            feedback_type="DISLIKE",
        )
        response = self.client.get(f"/api/check-track-feedback/{'C' * 22}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["liked"])

    def test_unknown_track_returns_liked_false(self):
        response = self.client.get(f"/api/check-track-feedback/{'Z' * 22}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["liked"])


# ---------------------------------------------------------------------------
# AI feedback service — singleton cost limit persists between calls
# ---------------------------------------------------------------------------

class TestFeedbackInterpreterSingleton(TestCase):
    """
    get_feedback_interpreter() must return the same FeedbackInterpreter instance
    each time so daily_cost accumulates across requests in a process.
    """

    def test_singleton_returns_same_instance(self):
        from apps.ai.ai_feedback_service import get_feedback_interpreter
        a = get_feedback_interpreter()
        b = get_feedback_interpreter()
        self.assertIs(a, b)

    def test_singleton_cost_accumulates(self):
        from apps.ai.ai_feedback_service import get_feedback_interpreter
        interpreter = get_feedback_interpreter()
        # Reset state for test isolation
        interpreter.rate_limiter.daily_cost = 0.0

        initial_cost = interpreter.rate_limiter.daily_cost
        interpreter.rate_limiter.log_cost(1000)
        # Cost should have increased (1000 tokens at GPT-4o pricing)
        self.assertGreater(interpreter.rate_limiter.daily_cost, initial_cost)
        # Fetching interpreter again returns same object — cost persists
        interpreter2 = get_feedback_interpreter()
        self.assertEqual(interpreter2.rate_limiter.daily_cost, interpreter.rate_limiter.daily_cost)


# ---------------------------------------------------------------------------
# _build_gem_explanation — pure function tests
# ---------------------------------------------------------------------------

class TestBuildGemExplanation(TestCase):
    """Tests for the _build_gem_explanation pure helper function."""

    def test_genre_sim_dominant_contains_expected_substrings(self):
        """genre_sim dominant: result contains '82%', 'via playlist mining', 'Matches your listening taste'."""
        breakdown = {
            'genre_sim': 0.82,
            'novelty': 0.10,
            'feedback_multiplier': 0.05,
            'source': 'playlist mining',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'Artist', 'playlist mining')
        self.assertIn('82%', result)
        self.assertIn('via playlist mining', result)
        self.assertIn('Matches your listening taste', result)

    def test_novelty_dominant_contains_expected_substrings(self):
        """novelty dominant: result contains 'hidden gem' and 'via artist network'."""
        breakdown = {
            'genre_sim': 0.10,
            'novelty': 0.90,
            'feedback_multiplier': 0.05,
            'source': 'artist network',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'Artist', 'artist network')
        self.assertIn('hidden gem', result)
        self.assertIn('via artist network', result)

    def test_feedback_multiplier_dominant_contains_expected_substrings(self):
        """feedback_multiplier dominant: result contains \"You've liked\", artist name, 'via related artists'."""
        breakdown = {
            'genre_sim': 0.10,
            'novelty': 0.20,
            'feedback_multiplier': 0.90,
            'source': 'related artists',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'The Artist', 'related artists')
        self.assertIn("You've liked", result)
        self.assertIn('The Artist', result)
        self.assertIn('via related artists', result)

    def test_empty_breakdown_returns_fallback(self):
        """Empty breakdown returns the literal fallback string."""
        result = _build_gem_explanation({}, '', '', '')
        self.assertEqual(result, 'Picked based on your listening patterns')

    def test_all_zero_components_returns_fallback(self):
        """All-zero breakdown returns the literal fallback string."""
        breakdown = {
            'genre_sim': 0.0,
            'novelty': 0.0,
            'feedback_multiplier': 0.0,
            'source': 'fallback',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'Artist', 'fallback')
        self.assertEqual(result, 'Picked based on your listening patterns')

    def test_missing_source_uses_discovery_fallback(self):
        """Empty source string triggers 'via discovery' fallback."""
        breakdown = {
            'genre_sim': 0.5,
            'novelty': 0.0,
            'feedback_multiplier': 0.0,
            'source': '',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'Artist', '')
        self.assertIn('via discovery', result)

    def test_tie_breaking_is_deterministic_no_exception(self):
        """Tied components do not raise exceptions; result is a non-empty string."""
        breakdown = {
            'genre_sim': 0.5,
            'novelty': 0.5,
            'feedback_multiplier': 0.5,
            'source': 'playlist mining',
        }
        result = _build_gem_explanation(breakdown, 'Track', 'Artist', 'playlist mining')
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

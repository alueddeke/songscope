"""
Phase 4 backend tests — metrics endpoints, Jaccard distance helper, taste vector validation.

Covers:
  - GET /api/recommendation-metrics/  (TestMetricsEndpoint, TestTasteVector)
  - GET /api/recommendation-trend/    (TestTrendEndpoint)
  - _jaccard_distance() helper        (TestJaccard)

Test isolation:
  - TestMetricsEndpoint, TestTrendEndpoint, TestTasteVector use django.test.TestCase
    (DB; each test wrapped in a transaction that rolls back automatically).
  - TestJaccard is a pure-unit test using unittest.TestCase (no DB, no Spotify API).

Django settings and django.setup() are handled by conftest.py — do NOT repeat here.
"""

import datetime
import unittest

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import DailyGem, RecommendationLog, Track, UserProfile
from apps.core.views import _jaccard_distance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_track(spotify_id, genres=None):
    """Create a Track row with optional genres list."""
    track, _ = Track.objects.get_or_create(
        spotify_id=spotify_id,
        defaults={
            'name': f'Track {spotify_id}',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'genres': genres or [],
        },
    )
    return track


def _make_gem(user, track, date, was_liked=None, track_popularity=50):
    """Create a DailyGem row."""
    return DailyGem.objects.create(
        user=user,
        track=track,
        date=date,
        was_liked=was_liked,
        track_popularity=track_popularity,
    )


# ---------------------------------------------------------------------------
# TestMetricsEndpoint — GET /api/recommendation-metrics/
# ---------------------------------------------------------------------------

class TestMetricsEndpoint(TestCase):
    """
    Tests for GET /api/recommendation-metrics/.

    Covers:
      - 'No gems yet' cold-start response
      - gem_acceptance_rate numeric type when gems exist with no feedback
      - hidden_gem_rate computed from track_popularity < 40 (not was_novel)
      - all 12 required response fields present
      - improvement_story first-7 vs last-7 calculation
      - improvement_story null branch for <2 gems
      - unauthenticated 403/401
    """

    ENDPOINT = '/api/recommendation-metrics/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_login(self.user)

    # --- Test 1 ---
    def test_returns_message_when_no_gems(self):
        """Authenticated GET with zero DailyGem rows → 200 + message key."""
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('message', data)
        self.assertTrue(data['message'])  # non-empty string

    # --- Test 2 ---
    def test_gem_acceptance_rate_is_numeric_when_no_feedback(self):
        """
        3 DailyGems all with was_liked=None → gem_acceptance_rate is numeric (0.0),
        not None. None is reserved for the zero-gems branch only.
        """
        today = datetime.date.today()
        track = _make_track('track-001')
        for i in range(3):
            _make_gem(self.user, track, today - datetime.timedelta(days=i),
                      was_liked=None, track_popularity=50)

        # Each gem needs a unique date — override track to allow uniqueness
        # (DailyGem has unique_together=['user', 'date'])
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('gem_acceptance_rate', data)
        self.assertIsInstance(data['gem_acceptance_rate'], (int, float))

    # --- Test 3 ---
    def test_hidden_gem_rate_uses_track_popularity_lt_40(self):
        """
        5 DailyGems with popularities [10, 30, 50, 70, 90].
        hidden_gem_rate == 2/5 == 0.4 (10 and 30 are < 40).
        RecommendationLog.was_novel must NOT affect this metric.
        """
        today = datetime.date.today()
        popularities = [10, 30, 50, 70, 90]
        for i, pop in enumerate(popularities):
            track = _make_track(f'pop-track-{i}')
            _make_gem(self.user, track, today - datetime.timedelta(days=i),
                      was_liked=True, track_popularity=pop)

        # Create a RecommendationLog with was_novel=True for an unrelated track
        # to confirm it has no influence on hidden_gem_rate.
        unrelated_track = _make_track('unrelated-001')
        RecommendationLog.objects.create(
            user=self.user, track=unrelated_track, was_novel=True
        )

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertAlmostEqual(data['hidden_gem_rate'], 0.4, places=4)

    # --- Test 4 ---
    def test_response_includes_all_phase4_fields(self):
        """
        When gems exist, response contains all 12 required keys:
        the 9 existing MetricsStrip fields + 3 Phase 4 extension fields.
        """
        today = datetime.date.today()
        track = _make_track('field-track-001')
        _make_gem(self.user, track, today, was_liked=True, track_popularity=30)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        required_fields = [
            'total_recommended',
            'avg_popularity',
            'novel_track_rate',
            'hidden_gem_rate',
            'gem_total',
            'gem_liked',
            'gem_disliked',
            'gem_acceptance_rate',
            'top_genres',
            'top_genres_pct',
            'improvement_story',
            'diversity_score',
        ]
        for field in required_fields:
            self.assertIn(field, data, msg=f"Missing field: {field}")

    # --- Test 5 ---
    def test_improvement_story_first_7_vs_last_7(self):
        """
        14 DailyGems: first 7 have 1 liked (rate 14%), last 7 have 5 liked (71%).
        Assert improvement_story rates and delta.
        """
        today = datetime.date.today()
        # was_liked pattern: first 7 → 1 like (index 0), last 7 → 5 likes (indices 7-11)
        liked_pattern = [True, False, False, False, False, False, False,
                         True,  True,  True,  True,  True,  False, False]
        for i, liked in enumerate(liked_pattern):
            track = _make_track(f'imp-track-{i}')
            _make_gem(self.user, track, today - datetime.timedelta(days=13 - i),
                      was_liked=liked, track_popularity=50)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        story = data['improvement_story']

        # first 7 gems: 1 liked / 7 total = 14%
        self.assertEqual(story['first_7_rate'], 14)
        # last 7 gems: 5 liked / 7 total = 71%
        self.assertEqual(story['last_7_rate'], 71)
        # delta = 71 - 14 = 57
        self.assertEqual(story['delta'], 57)

    # --- Test 6 ---
    def test_improvement_story_null_when_fewer_than_2_gems(self):
        """
        1 DailyGem → improvement_story leaves rates as None (cold-start, D-04).
        """
        today = datetime.date.today()
        track = _make_track('single-track-001')
        _make_gem(self.user, track, today, was_liked=True, track_popularity=50)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        story = data['improvement_story']
        # At least one leaf must be None in the cold-start branch
        self.assertTrue(
            story['first_7_rate'] is None or story['delta'] is None,
            msg=f"Expected at least one None in improvement_story for <2 gems: {story}"
        )

    # --- Test 7 ---
    def test_unauthenticated_returns_403(self):
        """Unauthenticated GET → 401 or 403 (IsAuthenticated enforced)."""
        from django.test import Client
        anon_client = Client()
        response = anon_client.get(self.ENDPOINT)
        self.assertIn(response.status_code, (401, 403))


# ---------------------------------------------------------------------------
# TestTrendEndpoint — GET /api/recommendation-trend/
# ---------------------------------------------------------------------------

class TestTrendEndpoint(TestCase):
    """Tests for GET /api/recommendation-trend/."""

    ENDPOINT = '/api/recommendation-trend/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='trenduser', password='testpass'
        )
        self.client.force_login(self.user)

    # --- Test 1 ---
    def test_returns_empty_data_with_message_when_fewer_than_2_dates(self):
        """
        0 or 1 DailyGem rows → response 200 with data=[] and a message key.
        """
        # Create only 1 gem (single date)
        today = datetime.date.today()
        track = _make_track('trend-single-track')
        DailyGem.objects.create(
            user=self.user, track=track, date=today, was_liked=True, track_popularity=50
        )

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data'], [])
        self.assertIn('message', data)
        self.assertTrue(data['message'])

    # --- Test 2 ---
    def test_rolling_7_day_window_correctness(self):
        """
        10 DailyGems on 10 consecutive days.
        was_liked = [T, T, T, F, F, F, F, T, T, T] (indices 0..9, oldest first).
        At the final date (index 9), the rolling 7-day window covers indices 3..9:
        [F, F, F, F, T, T, T] → 3 liked / 7 total ≈ 42.9%.
        """
        today = datetime.date.today()
        liked_pattern = [True, True, True, False, False, False, False, True, True, True]

        for i, liked in enumerate(liked_pattern):
            track = _make_track(f'trend-track-{i}')
            gem_date = today - datetime.timedelta(days=9 - i)
            DailyGem.objects.create(
                user=self.user, track=track, date=gem_date,
                was_liked=liked, track_popularity=50
            )

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data_obj = response.json()
        points = data_obj['data']

        # Should have exactly 10 points (one per gem date)
        self.assertEqual(len(points), 10)

        # Each point must have 'date' (YYYY-MM-DD) and 'like_rate' (float)
        for point in points:
            self.assertIn('date', point)
            self.assertIn('like_rate', point)
            self.assertIsInstance(point['like_rate'], (int, float))

        # Final point: window covers last 7 gems → 3 liked / 7 = 42.857...%
        expected_final_rate = round(3 / 7 * 100, 1)
        self.assertAlmostEqual(points[-1]['like_rate'], expected_final_rate, places=1)

    # --- Test 3 ---
    def test_unauthenticated_returns_403(self):
        """Unauthenticated GET → 401 or 403."""
        from django.test import Client
        anon_client = Client()
        response = anon_client.get(self.ENDPOINT)
        self.assertIn(response.status_code, (401, 403))


# ---------------------------------------------------------------------------
# TestJaccard — _jaccard_distance() helper (pure unit, no DB)
# ---------------------------------------------------------------------------

class TestJaccard(unittest.TestCase):
    """
    Pure-unit tests for the _jaccard_distance(genres_a, genres_b) helper.
    Jaccard distance = 1 - |A ∩ B| / |A ∪ B|.
    Importable from apps.core.views (module-level function).
    """

    def test_jaccard_both_empty_is_zero(self):
        """jaccard_distance([], []) must return 0.0 (identical empty sets)."""
        self.assertEqual(_jaccard_distance([], []), 0.0)

    def test_jaccard_fully_disjoint_is_one(self):
        """
        jaccard_distance(['rock'], ['jazz']) must return 1.0.
        Intersection=empty, union={'rock','jazz'}, distance = 1 - 0/2 = 1.0.
        """
        self.assertEqual(_jaccard_distance(['rock'], ['jazz']), 1.0)

    def test_jaccard_partial_overlap(self):
        """
        jaccard_distance(['rock', 'jazz'], ['rock', 'pop']) ≈ 0.6667.
        Intersection={'rock'} (size 1), union={'rock','jazz','pop'} (size 3).
        Distance = 1 - 1/3 ≈ 0.6667.
        """
        result = _jaccard_distance(['rock', 'jazz'], ['rock', 'pop'])
        expected = 1 - 1 / 3
        self.assertAlmostEqual(result, expected, places=4)


# ---------------------------------------------------------------------------
# TestTasteVector — top_genres_pct computation
# ---------------------------------------------------------------------------

class TestTasteVector(TestCase):
    """
    Tests for top_genres_pct field returned by GET /api/recommendation-metrics/.

    top_genres_pct is a list of {'genre': str, 'pct': float} dicts,
    capped at 10 entries, where pct values sum to approximately 100.0.
    """

    ENDPOINT = '/api/recommendation-metrics/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='tasteuser', password='testpass'
        )
        self.client.force_login(self.user)
        # Ensure there is at least 1 gem so the endpoint returns data (not the no-gems branch)
        track = _make_track('taste-track-001')
        _make_gem(self.user, track, datetime.date.today(),
                  was_liked=True, track_popularity=50)

    # --- Test 8 ---
    def test_top_genres_pct_normalized_to_100(self):
        """
        UserProfile taste_vector = {'a': 3, 'b': 1, 'c': 1}.
        sum(pct values) must be approximately 100.0 (± 0.5).
        """
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.data['taste_vector'] = {'a': 3, 'b': 1, 'c': 1}
        profile.save()

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        pct_list = data['top_genres_pct']
        self.assertLessEqual(len(pct_list), 10)
        total_pct = sum(entry['pct'] for entry in pct_list)
        self.assertAlmostEqual(total_pct, 100.0, delta=0.5)

    # --- Test 9 ---
    def test_top_genres_capped_at_10(self):
        """
        taste_vector with 15 equal-count genres → len(top_genres) == 10
        AND len(top_genres_pct) == 10.
        """
        taste_vector = {f'genre_{i}': 1 for i in range(15)}
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.data['taste_vector'] = taste_vector
        profile.save()

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['top_genres']), 10)
        self.assertEqual(len(data['top_genres_pct']), 10)

"""
Phase 4 TDD stubs — metrics endpoints, Jaccard distance helper, and taste vector validation.

All tests start RED: they assert desired post-Phase-4 behaviour that the current
codebase does NOT satisfy. Wave 1 turns them GREEN by implementing:
  - GET /api/metrics/ (TestMetricsEndpoint)
  - GET /api/trends/ (TestTrendEndpoint)
  - jaccard_distance() helper (TestJaccard)
  - top_genres_pct computation (TestTasteVector)

Test isolation:
  - TestMetricsEndpoint, TestTrendEndpoint, TestTasteVector use django.test.TestCase
    (DB; each test wrapped in a transaction that rolls back automatically).
  - TestJaccard is a pure-unit test using unittest.TestCase (no DB, no Spotify API).

Django settings and django.setup() are handled by conftest.py — do NOT repeat here.
"""

import unittest

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import DailyGem, RecommendationLog, Track, UserProfile


# ---------------------------------------------------------------------------
# TestMetricsEndpoint — GET /api/metrics/ (3 stub methods)
# ---------------------------------------------------------------------------

class TestMetricsEndpoint(TestCase):
    """
    Tests for the /api/metrics/ endpoint that returns the MetricsStrip data
    (9 existing fields) plus 3 Phase 4 extension fields:
    top_genres_pct, improvement_story, diversity_score.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_login(self.user)

    def test_gem_acceptance_rate_is_none_when_zero_gems(self):
        """
        gem_acceptance_rate must be None (not 0 or 0.0) when the user has
        zero DailyGem records, so the UI can distinguish 'no data' from
        a genuinely zero acceptance rate.
        """
        # Wave 1: from apps.core.views import get_recommendation_metrics
        self.fail("Wave 1: implement gem_acceptance_rate null case")

    def test_hidden_gem_rate_uses_track_popularity_not_was_novel(self):
        """
        hidden_gem_rate is the fraction of liked DailyGems where
        DailyGem.track_popularity < 40. It must NOT use
        RecommendationLog.was_novel (always True per Pitfall 4 in
        04-RESEARCH.md), which would make the metric meaningless.
        """
        # Wave 1: from apps.core.views import get_recommendation_metrics
        # Setup: create two DailyGems — one low-pop (< 40), one high-pop (>= 40)
        # Assert: hidden_gem_rate == 0.5 (one of two liked gems qualifies)
        self.fail("Wave 1: implement hidden_gem_rate via track_popularity < 40")

    def test_response_contains_all_required_fields(self):
        """
        Response JSON must contain all 9 existing MetricsStrip fields
        (total_gems, liked_gems, disliked_gems, gem_acceptance_rate,
        hidden_gem_rate, avg_popularity, top_source, streak, diversity_score)
        plus the 3 Phase 4 extension fields:
        top_genres_pct, improvement_story, diversity_score.
        (diversity_score is in both lists — it's now computed properly.)
        """
        # Wave 1: from apps.core.views import get_recommendation_metrics
        # Required field set (12 total; diversity_score must not be a stub zero)
        required_fields = [
            'total_gems', 'liked_gems', 'disliked_gems',
            'gem_acceptance_rate', 'hidden_gem_rate', 'avg_popularity',
            'top_source', 'streak', 'diversity_score',
            'top_genres_pct', 'improvement_story',
        ]
        self.fail(
            "Wave 1: implement full /api/metrics/ response with fields: "
            + ", ".join(required_fields)
        )


# ---------------------------------------------------------------------------
# TestTrendEndpoint — GET /api/trends/ (2 stub methods)
# ---------------------------------------------------------------------------

class TestTrendEndpoint(TestCase):
    """
    Tests for the /api/trends/ endpoint that returns 7-day rolling
    acceptance-rate data for the LikeTrendChart.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='trenduser', password='testpass'
        )
        self.client.force_login(self.user)

    def test_returns_not_enough_data_message_when_fewer_than_two_dates(self):
        """
        When the user has fewer than 2 distinct DailyGem dates, the endpoint
        must return {'data': [], 'message': 'Not enough data'} so the
        frontend can render an empty-state instead of a broken chart.
        """
        # Wave 1: from apps.core.views import get_trend_data
        # Setup: zero gems OR only gems on a single date
        # Assert: response == {'data': [], 'message': 'Not enough data'}
        self.fail("Wave 1: implement 'Not enough data' guard for /api/trends/")

    def test_rolling_7_day_window_correctness_on_10_day_fixture(self):
        """
        Given a known 10-day fixture of DailyGem records, the rolling 7-day
        window acceptance rate must match the expected values. Day 8 should
        reflect gems on days 2–8 only (not day 1), confirming the window
        slides correctly.
        """
        # Wave 1: from apps.core.views import get_trend_data
        # Setup: create 10 DailyGems with known was_liked values across 10 dates
        # Assert: data[7]['acceptance_rate'] == computed_expected_value
        self.fail("Wave 1: implement 7-day rolling window for /api/trends/")


# ---------------------------------------------------------------------------
# TestJaccard — jaccard_distance() helper (3 stub methods)
# ---------------------------------------------------------------------------

class TestJaccard(unittest.TestCase):
    """
    Tests for the jaccard_distance(a, b) helper function that measures genre
    diversity. Jaccard distance = 1 - |A ∩ B| / |A ∪ B|.
    Used by diversity_score computation in the /api/metrics/ endpoint.
    """

    def test_jaccard_both_empty_is_zero(self):
        """
        jaccard_distance([], []) must return 0.0.
        Both sets are identical (empty), so distance = 1 - 1 = 0.
        (Convention: identical sets have distance 0, not undefined.)
        """
        # Wave 1: from apps.core.metrics_helpers import jaccard_distance
        self.fail("Wave 1: implement jaccard_distance([], []) == 0.0")

    def test_jaccard_fully_disjoint_is_one(self):
        """
        jaccard_distance(['rock'], ['jazz']) must return 1.0.
        Intersection = empty, union = {'rock', 'jazz'}, so distance = 1 - 0/2 = 1.0.
        (Fully disjoint genre sets per D-10 in 04-RESEARCH.md.)
        """
        # Wave 1: from apps.core.metrics_helpers import jaccard_distance
        self.fail("Wave 1: implement jaccard_distance(['rock'], ['jazz']) == 1.0")

    def test_jaccard_partial_overlap(self):
        """
        jaccard_distance(['rock', 'jazz'], ['rock', 'pop']) must return
        approximately 0.667 (= 1 - 1/3).
        Intersection = {'rock'} (size 1), union = {'rock', 'jazz', 'pop'} (size 3).
        Distance = 1 - 1/3 = 0.6666...

        Note: the stub records the CORRECT expected math (0.667), not a
        pre-computed wrong value.
        """
        # Wave 1: from apps.core.metrics_helpers import jaccard_distance
        # expected = 1 - (1 / 3)  # ≈ 0.667
        self.fail(
            "Wave 1: implement jaccard_distance(['rock','jazz'],['rock','pop'])"
            " == 1 - 1/3 ≈ 0.667"
        )


# ---------------------------------------------------------------------------
# TestTasteVector — top_genres_pct computation (2 stub methods)
# ---------------------------------------------------------------------------

class TestTasteVector(TestCase):
    """
    Tests for the top_genres_pct field returned by /api/metrics/.
    top_genres_pct is a list of dicts [{'genre': str, 'pct': float}, ...]
    capped at 10 entries, where pct values sum to approximately 100.0.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='tasteuser', password='testpass'
        )
        self.client.force_login(self.user)

    def test_top_genres_pct_has_at_most_10_entries(self):
        """
        top_genres_pct must contain at most 10 entries, even when the user's
        taste_vector has more than 10 distinct genres.
        Cap enforced by the metrics endpoint (not the taste vector builder).
        """
        # Wave 1: from apps.core.views import get_recommendation_metrics
        # Setup: UserProfile with taste_vector having 15+ genres
        # Assert: len(response['top_genres_pct']) <= 10
        self.fail("Wave 1: implement top_genres_pct capped at 10 entries")

    def test_top_genres_pct_sums_to_approximately_100(self):
        """
        The sum of all pct values in top_genres_pct must be approximately
        100.0, within a float tolerance of 0.5.
        This validates that percentages are correctly normalised from the
        raw genre counts in UserProfile.data['taste_vector'].
        """
        # Wave 1: from apps.core.views import get_recommendation_metrics
        # Setup: UserProfile with a known taste_vector (e.g., {'rock': 3, 'pop': 2})
        # Assert: abs(sum(e['pct'] for e in response['top_genres_pct']) - 100.0) <= 0.5
        self.fail(
            "Wave 1: implement top_genres_pct normalisation"
            " — sum of pct values must be ~100.0 (±0.5)"
        )

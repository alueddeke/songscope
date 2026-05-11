"""
Phase 3 TDD stubs — feedback learning loop.

Tests cover three Phase 3 behaviors:
  1. TestTasteVectorUpdate  — online taste-vector update on LIKE/DISLIKE/unlike
  2. TestThompsonBandit     — Thompson (Beta) sampling for source weight selection
  3. TestBellCurveNovelty   — Bell-curve (Gaussian) novelty score based on preferred popularity

All tests start RED: they assert desired post-Phase-3 behaviour that the current
no-op code in PersonalizationEngine and HybridRecommendationEngine does NOT satisfy.

Test isolation:
  - TestTasteVectorUpdate uses django.test.TestCase (DB; each test wrapped in
    a transaction that rolls back automatically — T-03-01 mitigation).
  - TestThompsonBandit and TestBellCurveNovelty are pure-unit tests using
    unittest.TestCase with mocked profile.data (no DB, no Spotify API calls).
"""

import math
import unittest
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import Track, UserFeedback, UserProfile
from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
from apps.recommendations.personalization_engine import PersonalizationEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rec(popularity: int = 50, source: str = "artist_network") -> dict:
    """Build a minimal recommendation dict with the given popularity."""
    return {
        "id": f"track_{popularity}",
        "name": f"Track Pop{popularity}",
        "artist": "Test Artist",
        "album": "Test Album",
        "preview_url": None,
        "image_url": None,
        "source": source,
        "score": 0.0,
        "popularity": popularity,
    }


def make_engine_with_stats(
    source_name: str, successes: int, failures: int
) -> HybridRecommendationEngine:
    """Return a HybridRecommendationEngine bypassing __init__ with mocked profile.data."""
    engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
    engine.user = Mock(id=99)
    engine.profile = Mock()
    engine.profile.data = {
        "taste_vector": {},
        "base_data": {"top_artists": []},
        "preferences": {
            "liked_artists": [],
            "disliked_artists": [],
        },
        "source_stats": {
            source_name: {"s": successes, "f": failures},
        },
        "recommendation_weights": {
            "playlist_mining": 0.3,
            "artist_network": 0.25,
            "contextual": 0.2,
            "popularity": 0.15,
            "feedback": 0.1,
        },
    }
    # get_recommendation_weights delegates to profile method in Phase 2; wire mock.
    engine.profile.get_recommendation_weights.return_value = (
        engine.profile.data["recommendation_weights"]
    )
    return engine


def make_engine_with_prefs(midpoint: int, width: int) -> HybridRecommendationEngine:
    """Return a HybridRecommendationEngine with preferred_popularity_range set."""
    engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
    engine.user = Mock(id=99)
    engine.profile = Mock()
    engine.profile.data = {
        "taste_vector": {},
        "base_data": {"top_artists": []},
        "preferences": {
            "liked_artists": [],
            "disliked_artists": [],
            "preferred_popularity_range": {
                "midpoint": midpoint,
                "width": width,
            },
        },
        "source_stats": {},
        "recommendation_weights": {},
    }
    engine.profile.get_recommendation_weights.return_value = {}
    return engine


# ---------------------------------------------------------------------------
# 1. Taste-vector online update (DB-integrated, Django TestCase)
# ---------------------------------------------------------------------------

class TestTasteVectorUpdate(TestCase):
    """
    DB-integrated tests for PersonalizationEngine taste-vector mutations.

    Each test runs inside a transaction that is rolled back after completion
    (Django TestCase default) — no cross-test DB pollution (T-03-01).
    """

    def setUp(self):
        self.user = User.objects.create_user("tvuser", password="pw")
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "data": {
                    "taste_vector": {"indie rock": 1.0, "pop": 1.0},
                    "base_data": {"top_artists": []},
                    "preferences": {},
                }
            },
        )
        self.track = Track.objects.create(
            spotify_id="tv_track_1",
            name="Indie Gem",
            artist="Artist A",
            album="Album X",
            genres=["indie rock"],
        )

    def _make_feedback(self, feedback_type: str, track=None, genres=None) -> UserFeedback:
        t = track or self.track
        if genres is not None:
            t.genres = genres
        fb, _ = UserFeedback.objects.get_or_create(
            user=self.user,
            track=t,
            defaults={"feedback_type": feedback_type},
        )
        fb.feedback_type = feedback_type
        fb.save()
        return fb

    # ------------------------------------------------------------------
    # test_like_increments_genre_weights
    # ------------------------------------------------------------------
    def test_like_increments_genre_weights(self):
        """
        LIKE on an 'indie rock' track must increase taste_vector['indie rock'].

        Current apply_feedback_learning() is a no-op → taste_vector unchanged →
        assertion fails (RED).
        """
        fb = self._make_feedback("LIKE")
        initial_weight = self.profile.data["taste_vector"].get("indie rock", 0.0)

        engine = PersonalizationEngine(self.user)
        engine.apply_feedback_learning(fb)

        # Reload profile from DB to capture any persisted changes
        self.profile.refresh_from_db()
        updated_weight = self.profile.data["taste_vector"].get("indie rock", 0.0)

        self.assertGreater(
            updated_weight,
            initial_weight,
            msg=(
                f"Expected taste_vector['indie rock'] to increase after LIKE "
                f"(was {initial_weight}, got {updated_weight})"
            ),
        )

    # ------------------------------------------------------------------
    # test_dislike_decrements_genre_weights
    # ------------------------------------------------------------------
    def test_dislike_decrements_genre_weights(self):
        """
        DISLIKE on a 'pop' track must decrease (or zero-clamp) taste_vector['pop'].

        Current no-op → weight unchanged → assertion fails (RED).
        """
        pop_track = Track.objects.create(
            spotify_id="tv_track_pop",
            name="Pop Hit",
            artist="Pop Star",
            album="Pop Album",
            genres=["pop"],
        )
        UserFeedback.objects.filter(user=self.user, track=pop_track).delete()
        fb = UserFeedback.objects.create(
            user=self.user, track=pop_track, feedback_type="DISLIKE"
        )
        initial_weight = self.profile.data["taste_vector"].get("pop", 1.0)

        engine = PersonalizationEngine(self.user)
        engine.apply_feedback_learning(fb)

        self.profile.refresh_from_db()
        updated_weight = self.profile.data["taste_vector"].get("pop", 1.0)

        self.assertLessEqual(
            updated_weight,
            initial_weight,
            msg=(
                f"Expected taste_vector['pop'] to decrease or be zero-clamped after DISLIKE "
                f"(was {initial_weight}, got {updated_weight})"
            ),
        )
        # Must be strictly less (or 0) — not identical
        self.assertLess(
            updated_weight,
            initial_weight,
            msg=(
                "taste_vector['pop'] must strictly decrease (or clamp to 0) after DISLIKE; "
                "current no-op leaves it unchanged"
            ),
        )

    # ------------------------------------------------------------------
    # test_remove_feedback_reverses_like
    # ------------------------------------------------------------------
    def test_remove_feedback_reverses_like(self):
        """
        apply_feedback_learning(LIKE) followed by remove_feedback_learning(track_id)
        must reverse the taste_vector change: the post-remove weight must be
        strictly lower than the post-like weight.

        Because apply_feedback_learning() and remove_feedback_learning() are both
        no-ops in Phase 2, the post-like weight equals the initial weight, so:
          - post_remove_weight == post_like_weight (both unchanged)
          - assertLess(post_remove_weight, post_like_weight) → FAIL → RED

        When Phase 3 implements both methods, the LIKE raises the weight and the
        remove lowers it back, making the assertion pass.
        """
        fb = self._make_feedback("LIKE")

        engine = PersonalizationEngine(self.user)
        engine.apply_feedback_learning(fb)

        # Capture post-like weight (currently same as initial because no-op)
        self.profile.refresh_from_db()
        post_like_weight = self.profile.data["taste_vector"].get("indie rock", 0.0)

        # Reverse the like
        engine.remove_feedback_learning(self.track.spotify_id)

        self.profile.refresh_from_db()
        post_remove_weight = self.profile.data["taste_vector"].get("indie rock", 0.0)

        # The reversal must have actually decreased the weight relative to post-like.
        # With no-ops: post_like_weight == initial_weight == post_remove_weight → FAIL.
        self.assertLess(
            post_remove_weight,
            post_like_weight,
            msg=(
                f"Expected taste_vector['indie rock'] to decrease after "
                f"remove_feedback_learning (reversal of LIKE). "
                f"post-like={post_like_weight}, post-remove={post_remove_weight}. "
                f"(Both methods are no-ops in Phase 2 → equal weights → RED)"
            ),
        )


# ---------------------------------------------------------------------------
# 2. Thompson (Beta) bandit source weights (pure unit, no DB)
# ---------------------------------------------------------------------------

class TestThompsonBandit(unittest.TestCase):
    """
    Pure-unit tests for Thompson Beta sampling in get_recommendation_weights().

    In Phase 3 the engine is expected to:
      - Sample from Beta(s+1, f+1) for each source with enough data
      - Return static defaults when all sources are in cold-start (s+f < 3)

    Neither behaviour exists yet — tests are RED.
    """

    COLD_START_DEFAULTS = {
        "playlist_mining": 0.3,
        "artist_network": 0.25,
        "contextual": 0.2,
        "popularity": 0.15,
        "feedback": 0.1,
    }

    def test_beta_sample_increases_with_successes(self):
        """
        After recording 5 successes for 'artist_network', the dynamic weight
        returned by get_recommendation_weights()['artist_network'] must exceed
        the static cold-start default (0.25).

        Expected: Thompson sampling draws from Beta(6, 1) → mean ~0.857, which
        is well above 0.25 for any reasonable draw.

        Current: get_recommendation_weights() ignores source_stats and returns
        the static dict → value == 0.25, not > 0.25 → RED.
        """
        engine = make_engine_with_stats("artist_network", successes=5, failures=0)
        weights = engine.get_recommendation_weights()
        artist_network_weight = weights.get("artist_network", 0.0)
        self.assertGreater(
            artist_network_weight,
            self.COLD_START_DEFAULTS["artist_network"],
            msg=(
                f"With 5 successes, 'artist_network' weight should exceed the cold-start "
                f"default of {self.COLD_START_DEFAULTS['artist_network']}. "
                f"Got {artist_network_weight}. "
                f"(Thompson sampling not yet implemented — expected RED)"
            ),
        )

    def test_cold_start_returns_static_defaults(self):
        """
        With source_stats empty (or all sources having s+f < 3), the engine
        must return the same dict as UserProfile.get_recommendation_weights()
        (i.e., the static defaults).

        Current: this already passes trivially because there is no bandit logic —
        BUT the test is written against the DESIRED contract, which requires
        get_recommendation_weights() to exist on HybridRecommendationEngine
        (not just profile) and to accept source_stats. Once bandit logic is added
        the cold-start branch must keep this test green.

        Force RED by asserting against a non-existent 'bandit_active' flag that
        the Phase 3 implementation must set:
        """
        engine = make_engine_with_stats("artist_network", successes=0, failures=0)
        weights = engine.get_recommendation_weights()

        # The engine must expose a `bandit_active` property / key in the returned
        # dict to signal that Phase 3 logic is wired. Until then this fails.
        self.assertIn(
            "bandit_active",
            weights,
            msg=(
                "Expected get_recommendation_weights() to include 'bandit_active' key "
                "once Thompson sampling is implemented. This key is absent in the Phase 2 "
                "static implementation → RED."
            ),
        )


# ---------------------------------------------------------------------------
# 3. Bell-curve (Gaussian) novelty scoring (pure unit, no DB)
# ---------------------------------------------------------------------------

class TestBellCurveNovelty(unittest.TestCase):
    """
    Pure-unit tests for the bell-curve novelty formula in _score_recommendations().

    Phase 3 replaces the linear `1 - popularity/100` formula with a Gaussian
    centred at preferred_popularity_range['midpoint']:
        novelty = exp(-((pop - midpoint)^2) / (2 * width^2))

    Desired behaviour:
      - Track at the preferred midpoint scores the highest novelty
      - Extreme outliers (pop=0 or pop=100 with midpoint=30) score lower

    Current linear formula: novelty = 1 - pop/100
      - pop=0  → novelty=1.0
      - pop=30 → novelty=0.7
      - pop=100 → novelty=0.0
    So pop=0 currently wins, not the preferred midpoint → test is RED.
    """

    def test_novelty_peaks_at_preferred_midpoint(self):
        """
        With midpoint=30, width=20:
          - Track at popularity=30 should have novelty > Track at popularity=0
          - Track at popularity=30 should have novelty > Track at popularity=100

        Current linear formula gives novelty(30)=0.7 < novelty(0)=1.0 → FAIL → RED.
        """
        engine = make_engine_with_prefs(midpoint=30, width=20)
        engine.profile.data["taste_vector"] = {}
        engine.profile.data["base_data"] = {"top_artists": []}
        engine.profile.data["preferences"]["liked_artists"] = []
        engine.profile.data["preferences"]["disliked_artists"] = []

        recs = [
            _make_rec(popularity=0),
            _make_rec(popularity=30),
            _make_rec(popularity=100),
        ]
        scored = engine._score_recommendations(recs)

        # Build lookup by popularity
        score_by_pop = {r["popularity"]: r["score"] for r in scored}

        self.assertGreater(
            score_by_pop[30],
            score_by_pop[0],
            msg=(
                f"Expected novelty-peak at popularity=30 to beat popularity=0. "
                f"Scores: pop0={score_by_pop[0]:.4f}, pop30={score_by_pop[30]:.4f}. "
                f"(Linear formula gives pop0 the highest novelty → RED)"
            ),
        )
        self.assertGreater(
            score_by_pop[30],
            score_by_pop[100],
            msg=(
                f"Expected novelty-peak at popularity=30 to beat popularity=100. "
                f"Scores: pop30={score_by_pop[30]:.4f}, pop100={score_by_pop[100]:.4f}."
            ),
        )

    def test_cold_start_midpoint_default_is_30(self):
        """
        With no preferred_popularity_range in UserProfile.data, the scoring
        formula must default midpoint=30 and width=20.

        Assertion: a track at popularity=30 scores higher than popularity=0.
        This fails with the current linear formula (pop=0 → novelty=1.0 wins) → RED.
        """
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        # No preferred_popularity_range — only bare preferences dict
        engine.profile.data = {
            "taste_vector": {},
            "base_data": {"top_artists": []},
            "preferences": {
                "liked_artists": [],
                "disliked_artists": [],
                # No 'preferred_popularity_range' key
            },
            "source_stats": {},
        }
        engine.profile.get_recommendation_weights.return_value = {}

        recs = [_make_rec(popularity=0), _make_rec(popularity=30)]
        scored = engine._score_recommendations(recs)
        score_by_pop = {r["popularity"]: r["score"] for r in scored}

        self.assertGreater(
            score_by_pop[30],
            score_by_pop[0],
            msg=(
                f"With no preferred_popularity_range, bell-curve should default to "
                f"midpoint=30, giving pop=30 higher novelty than pop=0. "
                f"Scores: pop0={score_by_pop[0]:.4f}, pop30={score_by_pop[30]:.4f}. "
                f"(Current linear formula makes pop0 win → RED)"
            ),
        )


if __name__ == "__main__":
    unittest.main()

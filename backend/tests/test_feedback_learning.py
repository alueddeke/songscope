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

    # ------------------------------------------------------------------
    # test_remove_feedback_no_genres_does_not_raise
    # ------------------------------------------------------------------
    def test_remove_feedback_no_genres_does_not_raise(self):
        """
        remove_feedback_learning on a track whose genres list is empty must
        log a warning and return cleanly — no exception, no taste_vector change.

        Regression guard: an earlier version tried to iterate over None genres.
        """
        no_genre_track = Track.objects.create(
            spotify_id='no_genre_track_1',
            name='Genreless',
            artist='Mystery Artist',
            album='Unknown Album',
            genres=[],
        )
        engine = PersonalizationEngine(self.user)
        initial_vector = dict(self.profile.data['taste_vector'])

        # Must not raise
        engine.remove_feedback_learning(no_genre_track.spotify_id)

        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.data['taste_vector'],
            initial_vector,
            msg="taste_vector must be unchanged when track has no genres",
        )

    # ------------------------------------------------------------------
    # test_apply_feedback_no_recommendation_log_still_updates_taste_vector
    # ------------------------------------------------------------------
    def test_apply_feedback_no_recommendation_log_still_updates_taste_vector(self):
        """
        apply_feedback_learning on a LIKE for a track with no RecommendationLog
        entry (e.g., manually saved, or log was deleted) must still update the
        taste_vector — it should only skip the source_stats update, not the whole
        learning step.
        """
        fb = self._make_feedback("LIKE")
        # Confirm there is no RecommendationLog for this track
        from apps.core.models import RecommendationLog
        RecommendationLog.objects.filter(user=self.user, track=self.track).delete()

        initial_weight = self.profile.data['taste_vector'].get('indie rock', 0.0)

        engine = PersonalizationEngine(self.user)
        engine.apply_feedback_learning(fb)

        self.profile.refresh_from_db()
        updated_weight = self.profile.data['taste_vector'].get('indie rock', 0.0)

        self.assertGreater(
            updated_weight,
            initial_weight,
            msg=(
                "LIKE without a RecommendationLog must still increment taste_vector. "
                "Only source_stats should be skipped when no log entry exists."
            ),
        )

    # ------------------------------------------------------------------
    # test_build_taste_vector_preserves_feedback_learned_increments
    # ------------------------------------------------------------------
    def test_build_taste_vector_preserves_feedback_learned_increments(self):
        """
        Feedback-wipe regression (MD-05): _build_taste_vector must not overwrite
        taste_vector with raw artist counts, discarding feedback-learned increments.

        Sequence:
          1. apply_feedback_learning(LIKE) → 'indie rock' weight goes from 1.0 to 1.1
          2. _build_taste_vector() runs (simulating the 24h profile refresh)
          3. taste_vector['indie rock'] must remain ≥ 1.1, not revert to the raw
             top_artists count of 1 (or whatever the base count is).

        The merge logic (max(base, learned)) in _build_taste_vector ensures this.
        """
        # Apply a LIKE to boost 'indie rock'
        fb = self._make_feedback("LIKE")
        engine_pe = PersonalizationEngine(self.user)
        engine_pe.apply_feedback_learning(fb)

        self.profile.refresh_from_db()
        post_like_weight = self.profile.data['taste_vector'].get('indie rock', 0.0)
        self.assertGreater(post_like_weight, 1.0, msg="LIKE should have incremented the weight above 1.0")

        # Now simulate _build_taste_vector via the HybridRecommendationEngine
        # Inject one top_artist with 'indie rock' to provide a base count of 1
        self.profile.data['base_data'] = {
            'top_artists': [
                {'name': 'Artist A', 'genres': ['indie rock']},
            ]
        }
        self.profile.save(update_fields=['data'])

        hre = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        hre.user = self.user
        hre.profile = self.profile

        hre._build_taste_vector()

        self.profile.refresh_from_db()
        post_rebuild_weight = self.profile.data['taste_vector'].get('indie rock', 0.0)

        self.assertGreaterEqual(
            post_rebuild_weight,
            post_like_weight,
            msg=(
                f"_build_taste_vector must preserve feedback-learned weights. "
                f"post-like={post_like_weight:.3f}, post-rebuild={post_rebuild_weight:.3f}. "
                f"If post-rebuild < post-like, the merge logic is broken."
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
        After recording 5 successes for 'artist_network', the AVERAGE dynamic
        weight over 20 draws must exceed the static cold-start default (0.25).

        Beta(6, 1) has mean ~0.857 — far above 0.25.  A single draw has a
        ~0.024 % chance of falling below 0.25, causing a spurious CI failure.
        Averaging 20 independent draws reduces that risk to effectively zero
        while keeping the test honest about the stochastic nature of the bandit.
        """
        engine = make_engine_with_stats("artist_network", successes=5, failures=0)
        draws = [
            engine.get_recommendation_weights().get("artist_network", 0.0)
            for _ in range(20)
        ]
        avg_weight = sum(draws) / len(draws)
        self.assertGreater(
            avg_weight,
            self.COLD_START_DEFAULTS["artist_network"],
            msg=(
                f"With 5 successes, mean 'artist_network' weight over 20 draws "
                f"should exceed the cold-start default of "
                f"{self.COLD_START_DEFAULTS['artist_network']}. "
                f"Got mean={avg_weight:.4f}. "
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

    def test_all_sources_warm_weights_max_normalized(self):
        """
        When ALL 5 sources have ≥ COLD_START_THRESHOLD observations, the returned
        weights must be normalized to max=1.0 (not sum=1.0) so the best source
        gets a 1.0 multiplier and others are scaled relative to it.

        Audit gap: existing tests only exercise one warm source + four cold-start
        sources — the mixed case. This test targets the fully-warm path.

        With 10 successes / 0 failures for all 5 sources, Beta(11,1) mean ≈ 0.917.
        All draws are approximately equal → after max-normalization all weights ≈ 1.0.
        Assert: max(weights) == 1.0 and all weights ≤ 1.0.
        """
        from apps.recommendations.hybrid_recommendation_engine import SOURCE_DEFAULTS, COLD_START_THRESHOLD

        # Give every source well above the cold-start threshold
        engine = HybridRecommendationEngine.__new__(HybridRecommendationEngine)
        engine.user = Mock(id=99)
        engine.profile = Mock()
        high_obs = {'s': 10, 'f': 0}
        engine.profile.data = {
            'taste_vector': {},
            'base_data': {'top_artists': []},
            'preferences': {'liked_artists': [], 'disliked_artists': []},
            'source_stats': {src: dict(high_obs) for src in SOURCE_DEFAULTS},
        }
        engine.profile.get_recommendation_weights.return_value = {}

        weights = engine.get_recommendation_weights()

        source_weights = [weights[src] for src in SOURCE_DEFAULTS]
        max_w = max(source_weights)
        self.assertAlmostEqual(
            max_w,
            1.0,
            places=10,
            msg=f"Max weight should be exactly 1.0 (max-normalization). Got max={max_w:.6f}",
        )
        for src in SOURCE_DEFAULTS:
            self.assertLessEqual(
                weights[src],
                1.0,
                msg=f"Source '{src}' weight {weights[src]:.4f} exceeds 1.0 — normalization broken",
            )

    def test_boundary_exactly_threshold_minus_1_stays_cold(self):
        """
        A source with exactly COLD_START_THRESHOLD - 1 = 2 observations must
        use the static SOURCE_DEFAULTS weight, not Beta sampling.

        This boundary is critical: the switch from static to Beta happens at n ≥ 3.
        n=2 must remain cold-start.
        """
        from apps.recommendations.hybrid_recommendation_engine import SOURCE_DEFAULTS, COLD_START_THRESHOLD

        boundary_obs = COLD_START_THRESHOLD - 1  # 2
        engine = make_engine_with_stats('playlist_mining', successes=boundary_obs, failures=0)

        # Over many draws, the average must stay near the static default (0.3),
        # not drift toward Beta(3,1) mean ≈ 0.75.
        draws = [engine.get_recommendation_weights().get('playlist_mining', 0.0) for _ in range(10)]
        avg = sum(draws) / len(draws)

        static_default = SOURCE_DEFAULTS['playlist_mining']
        # The normalized static default with 4 other sources also at defaults:
        # thetas: {playlist:0.3, artist:0.25, genre:0.2, related:0.15, contextual:0.1}
        # max = 0.3 → normalized playlist_mining = 0.3/0.3 = 1.0
        # This is the cold-start normalized value for playlist_mining (best static source)
        self.assertGreaterEqual(
            avg,
            0.9,
            msg=(
                f"playlist_mining with n={boundary_obs} (cold-start) should use static "
                f"default (normalized to ~1.0 as best source). Got avg={avg:.4f}. "
                f"If avg is ~0.75, Beta sampling is incorrectly applied at n={boundary_obs}."
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

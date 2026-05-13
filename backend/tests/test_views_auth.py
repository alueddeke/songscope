"""
Auth flow coverage — spotify_callback edge cases.

Covers two HIGH-risk paths identified in the backend audit (test_coverage_gaps table):
  1. spotify_callback with missing oauth_state → 400, no user created
  2. spotify_callback when Spotify returns no refresh_token → stores '' not 'None'
"""
import json
from unittest.mock import patch, Mock, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import SpotifyToken


class TestSpotifyCallback(TestCase):
    """View-level tests for the OAuth callback edge cases."""

    # -----------------------------------------------------------------------
    # 1. Missing oauth_state
    # -----------------------------------------------------------------------
    def test_missing_oauth_state_returns_400(self):
        """
        If oauth_state is not in the session (e.g., the user navigated directly to the
        callback URL or the session expired), the view must return 400 and must NOT
        create any DB rows.

        The guard at views.py:62 already implements this; this test pins the behaviour
        so it cannot be accidentally removed.
        """
        # No session state set — simulate expired/missing session
        response = self.client.get('/spotify/callback/?code=abc123&state=stale_state')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        # No user or token should have been created
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(SpotifyToken.objects.count(), 0)

    def test_missing_oauth_state_error_message_is_generic(self):
        """Error body must not leak internal state — just a human-readable message."""
        response = self.client.get('/spotify/callback/')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        # Must not expose Python exception text
        self.assertNotIn('Traceback', data.get('error', ''))
        self.assertNotIn('Exception', data.get('error', ''))

    # -----------------------------------------------------------------------
    # 2. No refresh_token from Spotify
    # -----------------------------------------------------------------------
    def test_no_refresh_token_stored_as_empty_string(self):
        """
        When Spotify's token response omits 'refresh_token' (valid for some OAuth
        grant types / re-auth flows), the view must store '' rather than the string
        literal 'None'.

        Bug documented in CR-07: `token.get('refresh_token')` returns None, and
        without the `or ''` guard it would be coerced to 'None' by Django's CharField.
        The fix `token.get('refresh_token') or ''` is already applied; this test
        pins the regression.
        """
        # Set oauth_state so the guard passes
        session = self.client.session
        session['oauth_state'] = 'valid_state'
        session.save()

        with patch('apps.core.views.OAuth2Session') as mock_oauth_cls:
            mock_session = MagicMock()
            mock_oauth_cls.return_value = mock_session

            # Spotify token response without refresh_token
            mock_session.fetch_token.return_value = {
                'access_token': 'acc_token_123',
                'expires_in': 3600,
                # 'refresh_token' intentionally absent
            }
            mock_session.get.return_value.json.return_value = {
                'id': 'spotify_user_abc',
                'email': 'user@example.com',
            }

            response = self.client.get(
                '/spotify/callback/?code=auth_code_xyz&state=valid_state'
            )

        # View should redirect (302) to the frontend profile page on success
        self.assertEqual(response.status_code, 302)

        # Verify SpotifyToken was created and refresh_token is empty string
        user = User.objects.get(username='spotify_user_abc')
        token = SpotifyToken.objects.get(user=user)

        self.assertEqual(
            token.refresh_token,
            '',
            msg=(
                f"Expected refresh_token='' when Spotify omits it. "
                f"Got: {token.refresh_token!r}. "
                f"If this is 'None' the CR-07 fix was reverted."
            ),
        )
        self.assertNotEqual(
            token.refresh_token,
            'None',
            msg="refresh_token must not be the string literal 'None' — CR-07 regression",
        )

    def test_successful_callback_creates_user_and_token(self):
        """
        Sanity: a fully-formed callback creates the User and SpotifyToken rows and
        redirects to the frontend.  Validates the happy path assumptions underlying
        the edge-case tests above.
        """
        session = self.client.session
        session['oauth_state'] = 'good_state'
        session.save()

        with patch('apps.core.views.OAuth2Session') as mock_oauth_cls:
            mock_session = MagicMock()
            mock_oauth_cls.return_value = mock_session
            mock_session.fetch_token.return_value = {
                'access_token': 'acc_good',
                'refresh_token': 'ref_good',
                'expires_in': 3600,
            }
            mock_session.get.return_value.json.return_value = {
                'id': 'good_spotify_user',
                'email': 'good@example.com',
            }

            response = self.client.get(
                '/spotify/callback/?code=good_code&state=good_state'
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='good_spotify_user').exists())
        token = SpotifyToken.objects.get(user__username='good_spotify_user')
        self.assertEqual(token.access_token, 'acc_good')
        self.assertEqual(token.refresh_token, 'ref_good')

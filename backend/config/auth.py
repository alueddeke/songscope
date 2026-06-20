from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, SessionAuthentication


class DemoModeAuthentication(BaseAuthentication):
    """
    Public no-login demo authentication.

    When settings.DEMO_MODE is True, every request is authenticated as the
    single seeded demo user (settings.DEMO_USER_ID, falling back to the first
    user that owns a Spotify token). No session cookie is required — this is
    what lets a recruiter open the deployed SongScope URL and use the app
    immediately, and it sidesteps the cross-domain session-cookie problem.

    Active ONLY when DEMO_MODE is True (default False). This deliberately
    bypasses per-user auth and must never be enabled for a real multi-user
    production deployment — it is a portfolio-demo tradeoff.
    """

    def authenticate(self, request):
        if not getattr(settings, "DEMO_MODE", False):
            return None
        user = self._get_demo_user()
        if user is None:
            return None
        return (user, None)

    @staticmethod
    def _get_demo_user():
        demo_id = getattr(settings, "DEMO_USER_ID", None)
        if demo_id:
            try:
                return User.objects.get(pk=demo_id)
            except User.DoesNotExist:
                pass
        # Fallback: first user that has a Spotify token (the seeded demo account)
        from apps.core.models import SpotifyToken
        token = SpotifyToken.objects.select_related("user").first()
        return token.user if token else None


class DemoUserMiddleware:
    """
    In DEMO_MODE, attach the seeded demo user to every request that isn't
    already authenticated. DemoModeAuthentication only covers DRF views; this
    also covers plain Django views guarded by @login_required (which would
    otherwise 302-redirect to a login page and surface as a 404 in the client,
    e.g. /api/user-top-artists/). Must sit AFTER AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "DEMO_MODE", False) and not request.user.is_authenticated:
            user = DemoModeAuthentication._get_demo_user()
            if user is not None:
                request.user = user
        return self.get_response(request)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication without CSRF enforcement.

    Safe for cross-origin API calls: CORS headers (CORS_ALLOWED_ORIGINS +
    CORS_ALLOW_CREDENTIALS) gate which origins can include credentials.
    CSRF protection is redundant when the API is not reachable by third-party
    HTML forms (no same-origin form submission path).
    """

    def enforce_csrf(self, request):
        return

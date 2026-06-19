from rest_framework.authentication import SessionAuthentication


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

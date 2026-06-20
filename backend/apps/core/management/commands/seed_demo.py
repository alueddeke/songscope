"""
Seed the single demo account used by DEMO_MODE.

On a fresh production database there is no demo user, so DemoModeAuthentication
would resolve to nobody and every request would 401. This command creates (or
updates) the demo User and its SpotifyToken from environment variables so the
public no-login demo works after a clean deploy.

Run once on the prod host after migrate, e.g.:
    python manage.py seed_demo

Required env:
    DEMO_USER_SPOTIFY_REFRESH_TOKEN  — the demo account's Spotify refresh token
Optional env:
    DEMO_USER_USERNAME  — defaults to "demo"
    DEMO_USER_SPOTIFY_ID — stored on the profile if provided
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decouple import config

from apps.core.models import SpotifyToken, UserProfile


class Command(BaseCommand):
    help = "Create/update the demo user + Spotify token for DEMO_MODE."

    def handle(self, *args, **options):
        refresh_token = config("DEMO_USER_SPOTIFY_REFRESH_TOKEN", default="")
        if not refresh_token:
            self.stderr.write(
                "DEMO_USER_SPOTIFY_REFRESH_TOKEN is not set — cannot seed demo account."
            )
            return

        username = config("DEMO_USER_USERNAME", default="demo")
        spotify_id = config("DEMO_USER_SPOTIFY_ID", default="")

        user, created = User.objects.get_or_create(username=username)
        self.stdout.write(f"Demo user {'created' if created else 'exists'}: {username} (id={user.id})")

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if spotify_id:
            profile.spotify_user_id = spotify_id
            profile.save(update_fields=["spotify_user_id"])

        # Store the refresh token with an already-expired access token so the
        # first API call triggers refresh_spotify_token() and mints a fresh one.
        token, t_created = SpotifyToken.objects.update_or_create(
            user=user,
            defaults={
                "access_token": "seed-placeholder",
                "refresh_token": refresh_token,
                "expires_at": timezone.now() - timedelta(seconds=60),
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Spotify token {'created' if t_created else 'updated'} for demo user "
                f"(refresh_token len={len(refresh_token)}). "
                f"Set DEMO_USER_ID={user.id} in env to pin it."
            )
        )

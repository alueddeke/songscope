# backend/myapp/utils.py

import base64
import hashlib
import os
from .models import SpotifyToken
import requests
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def get_spotipy_client(access_token):
    """Create a properly configured Spotipy client"""
    try:
        return spotipy.Spotify(auth=access_token)
    except Exception as e:
        logger.error(f"Failed to create Spotipy client: {str(e)}")
        raise


def refresh_spotify_token(spotify_token):
    """Refresh an expired Spotify access token"""
    try:
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': spotify_token.refresh_token,
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'client_secret': settings.SPOTIFY_CLIENT_SECRET
        }
        response = requests.post('https://accounts.spotify.com/api/token', data=data)
        response.raise_for_status()  # Raises exception for 4XX/5XX status codes
        
        new_token_info = response.json()
        
        spotify_token.access_token = new_token_info['access_token']
        spotify_token.expires_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
        if 'refresh_token' in new_token_info:
            spotify_token.refresh_token = new_token_info['refresh_token']
        spotify_token.save()
        
        return spotify_token
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to refresh Spotify token: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {str(e)}")
        raise

# security for oauth
def generate_code_verifier():
    """Generates a code verifier for PKCE."""
    return base64.urlsafe_b64encode(os.urandom(43)).decode('utf-8').rstrip('=')
# test security
def generate_code_challenge(verifier):
    """Generates a code challenge for PKCE using the given code verifier."""
    challenge = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')

# It queries the database for SpotifyToken objects associated with the given user. If one exists, it returns the first one; otherwise, it returns None.
def get_user_tokens(user):
    user_tokens = SpotifyToken.objects.filter(user=user)
    if user_tokens.exists():
        return user_tokens[0]
    else:
        return None

def update_or_create_user_tokens(user, access_token, token_type, expires_in, refresh_token):
    tokens = get_user_tokens(user)
    expires_in = timezone.now() + timezone.timedelta(seconds=expires_in)
    if tokens:
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in
        tokens.token_type = token_type
        tokens.save(update_fields=['access_token', 'refresh_token', 'expires_in', 'token_type'])
    else:
        tokens = SpotifyToken(user=user, access_token=access_token, refresh_token=refresh_token, token_type=token_type, expires_in=expires_in)
        tokens.save()

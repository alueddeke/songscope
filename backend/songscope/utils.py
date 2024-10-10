# backend/myapp/utils.py

import base64
import hashlib
import os
from .models import SpotifyToken
import requests
from django.utils import timezone
from datetime import timedelta

def get_spotify_client(access_token):
    return {
        'headers': {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    }

def refresh_spotify_token(spotify_token):
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': spotify_token.refresh_token,
        'client_id': 'your_client_id',  # Replace with your actual client ID
        'client_secret': 'your_client_secret'  # Replace with your actual client secret
    }
    response = requests.post('https://accounts.spotify.com/api/token', data=data)
    new_token_info = response.json()

    spotify_token.access_token = new_token_info['access_token']
    spotify_token.expires_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
    if 'refresh_token' in new_token_info:
        spotify_token.refresh_token = new_token_info['refresh_token']
    spotify_token.save()

    return spotify_token

def generate_code_verifier():
    """Generates a code verifier for PKCE."""
    return base64.urlsafe_b64encode(os.urandom(43)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    """Generates a code challenge for PKCE using the given code verifier."""
    challenge = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')

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

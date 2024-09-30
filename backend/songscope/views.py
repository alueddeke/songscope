from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from requests_oauthlib import OAuth2Session
from .models import SpotifyToken
import requests
import time
import json
import logging
import os


logger = logging.getLogger(__name__)

if settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = settings.SPOTIFY_CLIENT_ID
client_secret = settings.SPOTIFY_CLIENT_SECRET
redirect_uri = settings.SPOTIFY_REDIRECT_URI
scope = 'user-read-private user-read-email user-top-read'
authorization_base_url = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'

@require_http_methods(["GET"])
def spotify_login(request):
    spotify = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorization_url, state = spotify.authorization_url(authorization_base_url)
    request.session['oauth_state'] = state
    return redirect(authorization_url)


@require_http_methods(["GET"])
def spotify_callback(request):
    try:
        spotify = OAuth2Session(client_id, redirect_uri=redirect_uri)
        
        # Log the full request URL for debugging
        # logger.debug(f"Full callback URL: {request.build_absolute_uri()}")
        
        token = spotify.fetch_token(
            token_url,
            client_secret=client_secret,
            authorization_response=request.build_absolute_uri()
        )
        
        # logger.debug(f"Received token: {json.dumps(token, indent=2)}")
        
        user_info = spotify.get('https://api.spotify.com/v1/me').json()
        # logger.debug(f"User info: {json.dumps(user_info, indent=2)}")
        
        user, created = User.objects.get_or_create(
            username=user_info['id'],
            defaults={'email': user_info.get('email', '')}
        )
        
        spotify_token, _ = SpotifyToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': token['access_token'],
                'refresh_token': token.get('refresh_token'),
                'expires_in': token['expires_in'],
                'token_type': token['token_type']
            }
        )
        
        login(request, user)
        
        frontend_url = settings.FRONTEND_URL
        return redirect(f"{frontend_url}/profile")
    
    except Exception as e:
        # logger.error(f"Error in spotify_callback: {str(e)}", exc_info=True)
        return JsonResponse({'error': f"Failed to process callback: {str(e)}"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_top_tracks(request):
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'No Spotify token found'}, status=400)
    
    if spotify_token.is_expired():
        try:
            spotify_token = refresh_spotify_token(spotify_token)
        except Exception as e:
            return JsonResponse({'error': 'Failed to refresh Spotify token'}, status=500)
    
    headers = {
        'Authorization': f'Bearer {spotify_token.access_token}'
    }
    
    response = requests.get('https://api.spotify.com/v1/me/top/tracks', headers=headers)
    
    if response.status_code == 200:
        return JsonResponse(response.json())
    else:
        return JsonResponse({'error': 'Failed to fetch top tracks'}, status=response.status_code)

@login_required
def check_auth(request):
    return JsonResponse({'authenticated': True})

def refresh_spotify_token(spotify_token):
    refresh_token = spotify_token.refresh_token
    
    response = requests.post(token_url, data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    })
    
    if response.status_code == 200:
        new_token_info = response.json()
        
        spotify_token.access_token = new_token_info['access_token']
        spotify_token.expires_at = int(new_token_info['expires_in']) + int(time.time())
        if 'refresh_token' in new_token_info:
            spotify_token.refresh_token = new_token_info['refresh_token']
        spotify_token.save()
    else:
        raise Exception('Could not refresh Spotify token')
    
    return spotify_token
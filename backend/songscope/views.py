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
import time
import logging
from django.utils import timezone
from datetime import timedelta
import os
from django.http import JsonResponse
from .utils import get_spotify_client, refresh_spotify_token
import requests


logger = logging.getLogger(__name__)

if settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = settings.SPOTIFY_CLIENT_ID
client_secret = settings.SPOTIFY_CLIENT_SECRET
redirect_uri = settings.SPOTIFY_REDIRECT_URI
scope = 'user-read-private user-read-email user-top-read'
authorization_base_url = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'

def spotify_login(request):
    client_id = settings.SPOTIFY_CLIENT_ID
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    scope = 'user-read-private user-read-email user-top-read user-read-recently-played'
    authorization_base_url = 'https://accounts.spotify.com/authorize'

    spotify = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorization_url, state = spotify.authorization_url(authorization_base_url)

    request.session['oauth_state'] = state
    return redirect(authorization_url)


@require_http_methods(["GET"])
def spotify_callback(request):
    try:
        spotify = OAuth2Session(client_id, redirect_uri=redirect_uri)
        
        token = spotify.fetch_token(
            token_url,
            client_secret=client_secret,
            authorization_response=request.build_absolute_uri()
        )
        
        user_info = spotify.get('https://api.spotify.com/v1/me').json()
        
        user, created = User.objects.get_or_create(
            username=user_info['id'],
            defaults={'email': user_info.get('email', '')}
        )
        
        expires_at = timezone.now() + timedelta(seconds=token['expires_in'])
        
        spotify_token, _ = SpotifyToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': token['access_token'],
                'refresh_token': token.get('refresh_token'),
                'expires_in': token['expires_in'],
                'expires_at': expires_at,
                'token_type': token['token_type'],
                'scope': token['scope']  
            }
        )
        
        login(request, user)
        
        frontend_url = settings.FRONTEND_URL
        return redirect(f"{frontend_url}/profile")
    except Exception as e:
        logger.error(f"Error in spotify_callback: {str(e)}", exc_info=True)
        return JsonResponse({'error': f"Failed to process callback: {str(e)}"}, status=400)
    
    except Exception as e:
        logger.error(f"Error in spotify_callback: {str(e)}", exc_info=True)
        return JsonResponse({'error': f"Failed to process callback: {str(e)}"}, status=400)
  


@login_required
def get_user_top_tracks(request):
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        client = get_spotify_client(spotify_token.access_token)
        response = requests.get(
            'https://api.spotify.com/v1/me/top/tracks',
            headers=client['headers'],
            params={'limit': 12, 'time_range': 'short_term'}
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Failed to fetch top tracks from Spotify'}, status=response.status_code)
        
        top_tracks = response.json()
        
        tracks_data = [{
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
        } 
        #loop makes dictionary for each track in items - set to the defined limit 
        for track in top_tracks['items']]
        
        return JsonResponse({'tracks': tracks_data})
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
def get_user_recently_played(request):
    logger.info(f"Accessing recently played tracks for user: {request.user}")
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        logger.info(f"Spotify token found for user: {request.user}")
        if spotify_token.is_expired():
            logger.info(f"Refreshing expired token for user: {request.user}")
            spotify_token = refresh_spotify_token(spotify_token)
        
        client = get_spotify_client(spotify_token.access_token)
        response = requests.get(
            'https://api.spotify.com/v1/me/player/recently-played',
            headers=client['headers'],
            params={'limit': 50}
        )
        
        if response.status_code != 200:
            logger.error(f"Spotify API error: {response.status_code} - {response.text}")
            return JsonResponse({'error': 'Failed to fetch recently played tracks from Spotify'}, status=response.status_code)
        
        recent_tracks = response.json()
        
        tracks_data = [{
            'id': track['track']['id'],
            'name': track['track']['name'],
            'artist': track['track']['artists'][0]['name'],
            'played_at': track['played_at']
        } for track in recent_tracks['items']]
        
        logger.info(f"Successfully fetched {len(tracks_data)} recently played tracks for user: {request.user}")
        return JsonResponse({'recent_tracks': tracks_data})
    except SpotifyToken.DoesNotExist:
        logger.error(f"Spotify token not found for user: {request.user}")
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error fetching recently played tracks for user: {request.user}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_user_top_artists(request):
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        client = get_spotify_client(spotify_token.access_token)
        response = requests.get(
            'https://api.spotify.com/v1/me/top/artists',
            headers=client['headers'],
            params={'limit': 12, 'time_range': 'short_term'}
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Failed to fetch top artists from Spotify'}, status=response.status_code)
        
        top_artists = response.json()
        
        artists_data = [{
            'id': artist['id'],
            'name': artist['name'],
            'genres': artist['genres'],
            'popularity': artist['popularity']
        } for artist in top_artists['items']]
        
        return JsonResponse({'top_artists': artists_data})
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)






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
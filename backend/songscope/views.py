import json
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
from .utils import get_spotipy_client, refresh_spotify_token
import requests
from .feature_extractor import extract_current_user_profile, get_recommendations
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth
import numpy as np



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
    scope = 'user-read-private user-read-email user-top-read user-read-recently-played user-library-modify'
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
    """Get user's top tracks using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        # Use Spotipy client
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Single method call instead of raw request
        top_tracks = sp.current_user_top_tracks(
            limit=12, 
            time_range='short_term'
        )
        
        tracks_data = [{
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
        } for track in top_tracks['items']]
        
        return JsonResponse({'tracks': tracks_data})
        
    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_user_recently_played(request):
    """Get user's recently played tracks using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Single method call instead of raw request
        recent_tracks = sp.current_user_recently_played(limit=50)
        
        tracks_data = [{
            'id': track['track']['id'],
            'name': track['track']['name'],
            'artist': track['track']['artists'][0]['name'],
            'played_at': track['played_at']
        } for track in recent_tracks['items']]
        
        return JsonResponse({'recent_tracks': tracks_data})
        
    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_user_top_artists(request):
    """Get user's top artists using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Single method call instead of raw request
        top_artists = sp.current_user_top_artists(
            limit=12,
            time_range='short_term'
        )
        
        artists_data = [{
            'id': artist['id'],
            'name': artist['name'],
            'genres': artist['genres'],
            'popularity': artist['popularity']
        } for artist in top_artists['items']]
        
        return JsonResponse({'top_artists': artists_data})
        
    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_track_recommendations(request):
    """Get personalized track recommendations using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
            
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Get top tracks for seeds
        top_tracks = sp.current_user_top_tracks(
            limit=5,
            time_range='short_term'
        )
        
        # Extract seed track IDs
        seed_tracks = [track['id'] for track in top_tracks['items']]
        
        # Get audio features for personalization
        audio_features = sp.audio_features(seed_tracks)
        
        # Calculate average features for recommendations
        avg_features = {
            'target_tempo': sum(track['tempo'] for track in audio_features) / len(audio_features),
            'target_energy': sum(track['energy'] for track in audio_features) / len(audio_features),
            'target_danceability': sum(track['danceability'] for track in audio_features) / len(audio_features),
            'target_valence': sum(track['valence'] for track in audio_features) / len(audio_features)
        }
        
        # Get recommendations with personalized parameters
        recommendations = sp.recommendations(
            seed_tracks=seed_tracks,
            limit=18,
            **avg_features
        )
        
        processed_tracks = [{
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'preview_url': track.get('preview_url'),
            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
        } for track in recommendations['tracks']]
        
        return JsonResponse({'recommendations': processed_tracks})
        
    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
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


def get_spotify_api_client(access_token):
    """
    Create a Spotify API client using the access token
    """
    return spotipy.Spotify(auth=access_token)

@login_required
def get_user_name(request):
    """Get user's name using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Single method call instead of raw request
        user_name = sp.me()
        
        return JsonResponse({'user_name': user_name})
        
    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

def add_track_to_liked(request):
    """Get user's name using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)

        print("-------step 1 complete-------")

        payload = json.loads(request.body.decode('utf-8'))
        track_id = payload.get("track_id")  # Use .get() to access "track_id"

        print(track_id)

        print("-------step 2 complete-------", track_id)
        sp.current_user_saved_tracks_add([track_id])

        print("-------step 3 complete-------")
        return JsonResponse({'message': "all good"})

    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
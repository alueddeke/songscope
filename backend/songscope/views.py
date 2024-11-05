from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
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
from .models import SpotifyToken, Track, UserFeedback, UserPreferences, RecommendationLog
from .logging_config import logger, log_api_error, log_spotify_error
from .serializers import FeedbackSubmissionSerializer
from .recommendation_engine import RecommendationEngine

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not enforce CSRF token


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

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_track_recommendations(request):
#     """Get personalized track recommendations using Spotipy"""
#     try:
#         # Get and validate Spotify token
#         try:
#             spotify_token = SpotifyToken.objects.get(user=request.user)
#             if spotify_token.is_expired():
#                 spotify_token = refresh_spotify_token(spotify_token)
#         except SpotifyToken.DoesNotExist:
#             logger.error(f"No Spotify token found for user {request.user.id}")
#             return JsonResponse({'error': 'Spotify token not found'}, status=404)
#         except Exception as e:
#             log_api_error(e, "token refresh")
#             return JsonResponse({'error': 'Authentication error'}, status=401)

#         # Initialize Spotify client
#         try:
#             sp = get_spotipy_client(spotify_token.access_token)
#         except Exception as e:
#             log_api_error(e, "Spotify client initialization")
#             return JsonResponse({'error': 'Failed to initialize Spotify client'}, status=500)

#         # Get top tracks for seeds
#         try:
#             top_tracks = sp.current_user_top_tracks(
#                 limit=5,
#                 time_range='short_term'
#             )
#             if not top_tracks or 'items' not in top_tracks:
#                 logger.warning(f"No top tracks found for user {request.user.id}")
#                 return JsonResponse({'error': 'No top tracks available'}, status=404)
            
#             seed_tracks = [track['id'] for track in top_tracks['items']]
#         except SpotifyException as e:
#             log_spotify_error(e, "top tracks")
#             return JsonResponse({'error': 'Failed to fetch top tracks'}, status=e.http_status)
#         except Exception as e:
#             log_api_error(e, "top tracks fetch")
#             return JsonResponse({'error': 'Failed to process top tracks'}, status=500)

#         # Get audio features
#         try:
#             audio_features = sp.audio_features(seed_tracks)
#             if not audio_features or not any(audio_features):
#                 logger.warning(f"No audio features found for seed tracks")
#                 return JsonResponse({'error': 'No audio features available'}, status=404)
#         except SpotifyException as e:
#             log_spotify_error(e, "audio features")
#             return JsonResponse({'error': 'Failed to fetch audio features'}, status=e.http_status)
#         except Exception as e:
#             log_api_error(e, "audio features fetch")
#             return JsonResponse({'error': 'Failed to process audio features'}, status=500)

#         # Calculate target features
#         avg_features = {
#             'target_tempo': sum(track['tempo'] for track in audio_features if track) / len(audio_features),
#             'target_energy': sum(track['energy'] for track in audio_features if track) / len(audio_features),
#             'target_danceability': sum(track['danceability'] for track in audio_features if track) / len(audio_features),
#             'target_valence': sum(track['valence'] for track in audio_features if track) / len(audio_features)
#         }

#         # Get recommendations
#         try:
#             recommendations = sp.recommendations(
#                 seed_tracks=seed_tracks[:5],  # Ensure we don't exceed Spotify's limit
#                 limit=18,
#                 **avg_features
#             )
#             if not recommendations or 'tracks' not in recommendations:
#                 logger.warning("No recommendations returned from Spotify API")
#                 return JsonResponse({'error': 'No recommendations available'}, status=404)
#         except SpotifyException as e:
#             log_spotify_error(e, "recommendations")
#             return JsonResponse({'error': 'Failed to fetch recommendations'}, status=e.http_status)
#         except Exception as e:
#             log_api_error(e, "recommendations fetch")
#             return JsonResponse({'error': 'Failed to process recommendations'}, status=500)

#         # Process recommendations
#         processed_tracks = [{
#             'id': track['id'],
#             'name': track['name'],
#             'artist': track['artists'][0]['name'],
#             'album': track['album']['name'],
#             'preview_url': track.get('preview_url'),
#             'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
#         } for track in recommendations['tracks']]

#         return JsonResponse({'recommendations': processed_tracks})

#     except Exception as e:
#         logger.exception("Unexpected error in get_track_recommendations")
#         return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_track_recommendations(request):
    """Get personalized track recommendations using the recommendation engine"""
    try:
        # Get and validate Spotify token
        try:
            spotify_token = SpotifyToken.objects.get(user=request.user)
            if spotify_token.is_expired():
                spotify_token = refresh_spotify_token(spotify_token)
        except SpotifyToken.DoesNotExist:
            logger.error(f"No Spotify token found for user {request.user.id}")
            return JsonResponse({'error': 'Spotify token not found'}, status=404)

        # Initialize Spotify client
        sp = get_spotipy_client(spotify_token.access_token)

        # Get recommendations using the engine
        engine = RecommendationEngine(request.user)
        recommended_tracks = engine.get_personalized_recommendations(sp, limit=18)

        # Process recommendations for frontend
        processed_tracks = [{
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'preview_url': track.get('preview_url'),
            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
        } for track in recommended_tracks]

        # Log recommendations
        for track in processed_tracks:
            track_obj = Track.objects.get_or_create(spotify_id=track['id'])[0]
            RecommendationLog.log_recommendation(request.user, track_obj)

        return JsonResponse({'recommendations': processed_tracks})

    except Exception as e:
        logger.exception("Unexpected error in get_track_recommendations")
        RecommendationLog.log_error(request.user, str(e))
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

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

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'message': 'CSRF cookie set'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    """Handle feedback submission and update recommendations"""
    try:
        serializer = FeedbackSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'error': serializer.errors}, status=400)

        # Get or refresh Spotify token
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)

        sp = get_spotipy_client(spotify_token.access_token)
        
        # Get or create track
        track_id = serializer.validated_data['track_id']
        track, created = Track.objects.get_or_create(
            spotify_id=track_id,
            defaults={
                'name': '',
                'artist': '',
                'album': ''
            }
        )

        # Update track details if new or missing audio features
        if created or not track.audio_features:
            track_info = sp.track(track_id)
            audio_features = sp.audio_features([track_id])[0]
            artist_info = sp.artist(track_info['artists'][0]['id'])
            
            track.name = track_info['name']
            track.artist = track_info['artists'][0]['name']
            track.album = track_info['album']['name']
            track.popularity = track_info['popularity']
            track.audio_features = audio_features
            track.genres = artist_info['genres']
            track.save()

        # Create feedback entry
        feedback = UserFeedback.objects.create(
            user=request.user,
            track=track,
            feedback_type=serializer.validated_data['feedback_type'],
            track_features=track.audio_features
        )

        # Update recommendations using the engine
        engine = RecommendationEngine(request.user)
        engine.update_preferences(feedback)

        return JsonResponse({'status': 'success'})

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
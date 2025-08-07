import json
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
from .models import SpotifyToken, Track, UserFeedback, UserPreferences, RecommendationLog, AIFeedback
from .logging_config import logger, log_api_error, log_spotify_error
from .serializers import FeedbackSubmissionSerializer, AIFeedbackSubmissionSerializer
from .recommendation_engine import RecommendationEngine
from .hybrid_recommendation_engine import HybridRecommendationEngine
from .ai_feedback_service import FeedbackInterpreter, RateLimitExceeded, CostLimitExceeded

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not enforce CSRF token


logger = logging.getLogger(__name__)

if settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = settings.SPOTIFY_CLIENT_ID
client_secret = settings.SPOTIFY_CLIENT_SECRET
redirect_uri = settings.SPOTIFY_REDIRECT_URI
scope = 'user-read-private user-read-email user-top-read user-read-recently-played user-library-modify user-read-playback-state'
authorization_base_url = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'

def spotify_login(request):
    client_id = settings.SPOTIFY_CLIENT_ID
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    scope = 'user-read-private user-read-email user-top-read user-read-recently-played user-library-modify user-read-playback-state user-library-read playlist-read-private'
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
            'popularity': artist['popularity'],
            'images': artist['images']
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
def check_spotify_token(request):
    """Check if Spotify token is valid and refresh if needed"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        
        # Check if token is expired
        if spotify_token.is_expired():
            logger.info(f"Token expired for user {request.user.id}, refreshing...")
            spotify_token = refresh_spotify_token(spotify_token)
        
        # Test the token with a simple API call
        sp = get_spotipy_client(spotify_token.access_token)
        user_info = sp.current_user()
        
        return JsonResponse({
            'valid': True,
            'user_id': user_info['id'],
            'display_name': user_info.get('display_name', 'Unknown')
        })
        
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'No Spotify token found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking Spotify token: {str(e)}")
        return JsonResponse({'valid': False, 'error': str(e)}, status=500)

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

        # Get recommendations using the hybrid engine
        engine = HybridRecommendationEngine(request.user)
        
        # Check if user wants fresh recommendations
        force_fresh = request.GET.get('force_fresh', 'false').lower() == 'true'
        
        # Get recommendations (will use cache unless force_fresh=True)
        recommended_tracks = engine.get_recommendations(limit=10, force_fresh=force_fresh)
        
        # Log cache info for debugging
        cache_stats = engine.profile.get_cache_stats()
        logger.info(f"User {request.user.id} cache stats: {cache_stats}")

        if not recommended_tracks:
            logger.warning("No recommendations returned from engine")
            return JsonResponse({'recommendations': []})

        logger.info(f"Processing {len(recommended_tracks)} hybrid recommendations")
        logger.info(f"Sample track format: {recommended_tracks[0] if recommended_tracks else 'No tracks'}")

        # Process recommendations for frontend
        processed_tracks = []
        for track in recommended_tracks:
            try:
                # Handle both Spotify API format and our discovery engine format
                if 'artists' in track:
                    # Spotify API format
                    artist_name = track['artists'][0]['name']
                    album_name = track['album']['name']
                    image_url = track['album']['images'][0]['url'] if track['album']['images'] else None
                else:
                    # Our discovery engine format
                    artist_name = track.get('artist', 'Unknown Artist')
                    album_name = track.get('album', 'Unknown Album')
                    image_url = track.get('image_url')
                
                processed_track = {
                    'id': track['id'],
                    'name': track['name'],
                    'artist': artist_name,
                    'album': album_name,
                    'preview_url': track.get('preview_url'),
                    'image_url': image_url,
                    'source': track.get('source', 'unknown'),
                    'score': track.get('score', 0.0),
                    'popularity': track.get('popularity', 0)
                }
                processed_tracks.append(processed_track)
                
            except Exception as e:
                logger.error(f"Error processing track {track.get('id', 'unknown')}: {str(e)}")
                continue

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

@api_view(['GET'])
def debug_auth(request):
    """Debug endpoint to check authentication status"""
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else None,
        'session_id': request.session.session_key,
        'cookies': dict(request.COOKIES)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalization_summary(request):
    """Get a summary of the user's personalization profile"""
    try:
        from .personalization_engine import PersonalizationEngine
        personalization_engine = PersonalizationEngine(request.user)
        summary = personalization_engine.get_personalization_summary()
        return JsonResponse(summary)
    except Exception as e:
        logger.error(f"Error getting personalization summary: {str(e)}")
        return JsonResponse({'error': 'Failed to get personalization summary'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile_summary(request):
    """Get a summary of the user's hybrid profile"""
    try:
        engine = HybridRecommendationEngine(request.user)
        summary = engine.get_profile_summary()
        return JsonResponse(summary)
    except Exception as e:
        logger.error(f"Error getting user profile summary: {str(e)}")
        return JsonResponse({'error': 'Failed to get user profile summary'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """Manually trigger user profile update"""
    try:
        engine = HybridRecommendationEngine(request.user)
        engine._update_profile_data()
        return JsonResponse({'message': 'Profile updated successfully'})
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return JsonResponse({'error': 'Failed to update profile'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_spotify_recommendations(request):
    """Test endpoint to debug Spotify recommendations API"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Test 1: Simple recommendations with popular track
        try:
            logger.info("Testing simple recommendations...")
            # Try with minimal parameters first
            simple_recs = sp.recommendations(
                seed_tracks=['0c6xIDDpzE81m2q797ordA'],  # Different track ID
                limit=5
            )
            logger.info(f"Simple recommendations test: {len(simple_recs['tracks'])} tracks")
        except Exception as e:
            logger.error(f"Simple recommendations failed: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            simple_recs = None
        
        # Test 2: Get user's top tracks
        try:
            top_tracks = sp.current_user_top_tracks(limit=5)
            logger.info(f"Top tracks test: {len(top_tracks['items'])} tracks")
        except Exception as e:
            logger.error(f"Top tracks failed: {str(e)}")
            top_tracks = None
        
        # Test 3: Get audio features
        try:
            if top_tracks and top_tracks['items']:
                track_id = top_tracks['items'][0]['id']
                logger.info(f"Testing audio features for track: {track_id}")
                features = sp.audio_features([track_id])
                logger.info(f"Audio features test: {features[0] if features else 'None'}")
            else:
                features = None
        except Exception as e:
            logger.error(f"Audio features failed: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            features = None
        
        # Capture error messages
        simple_recs_error = None
        audio_features_error = None
        
        if simple_recs is None:
            try:
                sp.recommendations(seed_tracks=['0c6xIDDpzE81m2q797ordA'], limit=5)
            except Exception as e:
                simple_recs_error = str(e)
        
        if features is None and top_tracks and top_tracks['items']:
            try:
                sp.audio_features([top_tracks['items'][0]['id']])
            except Exception as e:
                audio_features_error = str(e)
        
        return JsonResponse({
            'simple_recommendations_working': simple_recs is not None,
            'top_tracks_working': top_tracks is not None,
            'audio_features_working': features is not None,
            'simple_recs_count': len(simple_recs['tracks']) if simple_recs else 0,
            'top_tracks_count': len(top_tracks['items']) if top_tracks else 0,
            'simple_recs_error': simple_recs_error,
            'audio_features_error': audio_features_error
        })
        
    except Exception as e:
        logger.error(f"Error in test_spotify_recommendations: {str(e)}")
        return JsonResponse({'error': f'Test failed: {str(e)}'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_simple_recommendations(request):
    """Simple recommendations endpoint for testing feedback"""
    try:
        # Return some popular tracks for testing feedback
        test_tracks = [
            {
                'id': '4iV5W9uYEdYUVa79Axb7Rh',
                'name': 'Blinding Lights',
                'artist': 'The Weeknd',
                'album': 'After Hours',
                'preview_url': 'https://p.scdn.co/mp3-preview/...',
                'image_url': 'https://i.scdn.co/image/...'
            },
            {
                'id': '0V3wPSX9ygBnCm8psKOegu',
                'name': 'As It Was',
                'artist': 'Harry Styles',
                'album': 'Harry\'s House',
                'preview_url': 'https://p.scdn.co/mp3-preview/...',
                'image_url': 'https://i.scdn.co/image/...'
            },
            {
                'id': '1Qrg8KdBHuXFu6GMcSFYyq',
                'name': 'Flowers',
                'artist': 'Miley Cyrus',
                'album': 'Endless Summer Vacation',
                'preview_url': 'https://p.scdn.co/mp3-preview/...',
                'image_url': 'https://i.scdn.co/image/...'
            }
        ]
        
        return JsonResponse({'recommendations': test_tracks})
        
    except Exception as e:
        logger.error(f"Error in get_simple_recommendations: {str(e)}")
        return JsonResponse({'error': f'Failed: {str(e)}'}, status=500)

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
        feedback_type = serializer.validated_data['feedback_type']
        
        track, created = Track.objects.get_or_create(
            spotify_id=track_id,
            defaults={
                'name': '',
                'artist': '',
                'album': ''
            }
        )

        # Update track details if new (without audio features since API is broken)
        if created:
            track_info = sp.track(track_id)
            artist_info = sp.artist(track_info['artists'][0]['id'])
            
            track.name = track_info['name']
            track.artist = track_info['artists'][0]['name']
            track.album = track_info['album']['name']
            track.popularity = track_info['popularity']
            track.genres = artist_info['genres']
            track.save()

        # Check if user already has feedback for this track
        existing_feedback = UserFeedback.objects.filter(
            user=request.user,
            track=track,
            feedback_type='LIKE'
        ).first()

        if feedback_type == 'LIKE' and existing_feedback:
            # User is unliking - remove the existing feedback
            existing_feedback.delete()
            logger.info(f"Removed LIKE feedback for track {track.name}")
            
            # Update recommendations to reflect the removal
            from .personalization_engine import PersonalizationEngine
            personalization_engine = PersonalizationEngine(request.user)
            personalization_engine.remove_feedback_learning(track.spotify_id)
            
            # Also update hybrid profile
            hybrid_engine = HybridRecommendationEngine(request.user)
            hybrid_engine.remove_feedback(track.spotify_id)
            
            return JsonResponse({'status': 'success', 'action': 'removed'})
        else:
            # Create new feedback entry (without audio features)
            feedback = UserFeedback.objects.create(
                user=request.user,
                track=track,
                feedback_type=feedback_type,
                track_features={}  # Empty since we can't get audio features
            )

            # Update recommendations using the enhanced personalization engine
            from .personalization_engine import PersonalizationEngine
            personalization_engine = PersonalizationEngine(request.user)
            personalization_engine.apply_feedback_learning(feedback)
            
            # Also update hybrid profile
            hybrid_engine = HybridRecommendationEngine(request.user)
            track_info = {
                'artist': track.artist,
                'name': track.name,
                'album': track.album
            }
            hybrid_engine.add_feedback(track.spotify_id, feedback.feedback_type, track_info)
            
            logger.info(f"Feedback processed: {feedback.feedback_type} for track {track.name}")

            return JsonResponse({'status': 'success', 'action': 'added'})

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return JsonResponse({'error': 'Failed to submit feedback'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_ai_feedback(request):
    """Handle AI-powered feedback submission"""
    try:
        serializer = AIFeedbackSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'error': serializer.errors}, status=400)

        feedback_text = serializer.validated_data['feedback_text']
        track_id = serializer.validated_data.get('track_id', '')
        
        # Get track info if provided
        track_info = None
        track = None
        if track_id:
            try:
                track = Track.objects.get(spotify_id=track_id)
                track_info = {
                    'name': track.name,
                    'artist': track.artist,
                    'album': track.album
                }
            except Track.DoesNotExist:
                logger.warning(f"Track {track_id} not found for AI feedback")
        
        # Initialize AI feedback interpreter
        interpreter = FeedbackInterpreter()
        
        try:
            # Interpret the feedback
            interpretation = interpreter.interpret_feedback(feedback_text, track_info)
            
            # Store the AI feedback
            ai_feedback = AIFeedback.objects.create(
                user=request.user,
                track=track,
                original_text=feedback_text,
                interpretation=interpretation,
                confidence=interpretation.get('confidence', 0.0)
            )
            
            # Update hybrid recommendation engine with AI feedback
            hybrid_engine = HybridRecommendationEngine(request.user)
            hybrid_engine.add_ai_feedback(interpretation, track_info)
            
            logger.info(f"AI feedback processed: {feedback_text[:50]}...")
            
            return JsonResponse({
                'status': 'success',
                'interpretation': interpretation,
                'confidence': interpretation.get('confidence', 0.0)
            })
            
        except RateLimitExceeded:
            return JsonResponse({
                'error': 'Rate limit exceeded. Please try again later.',
                'status': 'rate_limit_exceeded'
            }, status=429)
            
        except CostLimitExceeded as e:
            return JsonResponse({
                'error': 'Daily cost limit exceeded. Please try again tomorrow.',
                'status': 'cost_limit_exceeded'
            }, status=429)
            
    except Exception as e:
        logger.error(f"Error submitting AI feedback: {str(e)}")
        return JsonResponse({'error': 'Failed to process feedback'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_track_feedback(request, track_id):
    """Check if user has already given feedback for a specific track"""
    try:
        # Check if user has liked this track
        track = Track.objects.filter(spotify_id=track_id).first()
        if not track:
            return JsonResponse({'liked': False})
        
        feedback = UserFeedback.objects.filter(
            user=request.user,
            track=track,
            feedback_type='LIKE'
        ).first()
        
        return JsonResponse({'liked': feedback is not None})
        
    except Exception as e:
        logger.error(f"Error checking track feedback: {str(e)}")
        return JsonResponse({'error': 'Failed to check feedback'}, status=500)

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

        payload = json.loads(request.body.decode('utf-8'))
        track_id = payload.get("track_id")

        sp.current_user_saved_tracks_add([track_id])

        return JsonResponse({'message': "all good"})

    except SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=e.http_status)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
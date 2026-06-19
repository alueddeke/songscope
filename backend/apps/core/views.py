import json
import os
from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta  # date removed: using timezone.localdate() everywhere
from itertools import combinations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from requests_oauthlib import OAuth2Session
import spotipy
from spotipy.exceptions import SpotifyException

from .models import SpotifyToken, Track, UserFeedback, RecommendationLog, AIFeedback, DailyGem, UserProfile
from .serializers import FeedbackSubmissionSerializer, AIFeedbackSubmissionSerializer
from apps.spotify.utils import get_spotipy_client, refresh_spotify_token
from apps.recommendations.hybrid_recommendation_engine import HybridRecommendationEngine
from apps.ai.ai_feedback_service import get_feedback_interpreter, RateLimitExceeded, CostLimitExceeded
from utils.logging_config import logger

if settings.OAUTHLIB_INSECURE_TRANSPORT:
    if not settings.DEBUG:
        import logging as _logging
        _logging.critical(
            "OAUTHLIB_INSECURE_TRANSPORT is enabled but DEBUG=False. "
            "This allows plain-HTTP OAuth in production — set OAUTHLIB_INSECURE_TRANSPORT=False."
        )
    else:
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
        state = request.session.get('oauth_state')
        if not state:
            return JsonResponse({'error': 'Missing OAuth state'}, status=400)
        spotify = OAuth2Session(client_id, state=state, redirect_uri=redirect_uri)

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
                'refresh_token': token.get('refresh_token') or '',
                'expires_at': expires_at,
            }
        )
        
        login(request, user)
        
        frontend_url = settings.FRONTEND_URL
        return redirect(f"{frontend_url}/profile")
    except Exception as e:
        logger.error(f"Error in spotify_callback: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Authentication failed. Please try again.'}, status=400)

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
        logger.error(f"Spotify API error in get_user_top_tracks: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_user_top_tracks: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

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
        logger.error(f"Spotify API error in get_user_recently_played: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_user_recently_played: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@login_required
def get_user_top_artists(request):
    """Get user's top artists using Spotipy with time range filter"""
    try:
        # Get time range from query parameters
        time_range = request.GET.get('time_range', 'week')
        
        # Validate time range and map to Spotify API values
        # Note: Spotify API limitations - we can only use their predefined ranges
        # short_term = ~4 weeks, medium_term = ~6 months, long_term = ~12 months
        valid_time_ranges = {
            '4 weeks': 'short_term',      # Last ~4 weeks (closest to 7 days)
            '6 months': 'medium_term',    # Last ~6 months (closest to 30 days) 
            'year': 'long_term'        # Last ~12 months
        }
        
        if time_range not in valid_time_ranges:
            time_range = '4 weeks'  # Default to 4 weeks
        
        spotify_time_range = valid_time_ranges[time_range]
        
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Get top artists with specified time range
        top_artists = sp.current_user_top_artists(
            limit=20,  # Increased limit for better variety
            time_range=spotify_time_range
        )
        
        artists_data = [{
            'id': artist['id'],
            'name': artist['name'],
            'genres': artist['genres'],
            'popularity': artist['popularity'],
            'images': artist['images'],
            'time_range': time_range  # Include the time range in response
        } for artist in top_artists['items']]
        
        logger.info(f"Retrieved {len(artists_data)} top artists for time range: {time_range}")
        
        return JsonResponse({
            'top_artists': artists_data,
            'time_range': time_range,
            'total_count': len(artists_data)
        })
        
    except SpotifyException as e:
        logger.error(f"Spotify API error in get_user_top_artists: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_user_top_artists: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


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
        logger.error(f"Error checking Spotify token: {str(e)}", exc_info=True)
        return JsonResponse({'valid': False, 'error': 'An unexpected error occurred'}, status=500)

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
            try:
                track_obj = Track.objects.get_or_create(
                    spotify_id=track['id'],
                    defaults={
                        'name': track.get('name', ''),
                        'artist': track.get('artist', ''),
                        'album': track.get('album', ''),
                    }
                )[0]
                RecommendationLog.log_recommendation(request.user, track_obj, source=track.get('source', ''))
            except Exception as log_err:
                logger.error(f"Error logging recommendation for track {track.get('id')}: {log_err}")

        return JsonResponse({'recommendations': processed_tracks})

    except Exception as e:
        logger.exception("Unexpected error in get_track_recommendations")
        RecommendationLog.log_error(request.user, str(e))
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@login_required
def check_auth(request):
    return JsonResponse({'authenticated': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_auth(request):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Not found'}, status=404)
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else None,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalization_summary(request):
    """Get a summary of the user's personalization profile"""
    try:
        from apps.recommendations.personalization_engine import PersonalizationEngine
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

def _jaccard_distance(genres_a: list, genres_b: list) -> float:
    """
    Compute Jaccard distance between two genre lists.

    Jaccard distance = 1 - |A ∩ B| / |A ∪ B|.
    Convention: both empty → 0.0 (identical empty sets, distance zero).
    If union is empty after dedup → 0.0 (guard against ZeroDivisionError).
    """
    a, b = set(genres_a), set(genres_b)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - len(a & b) / len(union)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_metrics(request):
    """
    Return on-the-fly recommendation metrics for the authenticated user.

    Satisfies the MetricsStrip LOCKED interface (D-02) plus Phase 4 extension
    fields (top_genres_pct, improvement_story, diversity_score).
    All metrics computed from DailyGem + UserProfile.data — no new DB columns (D-01).
    """
    try:
        user = request.user
        gems = DailyGem.objects.filter(user=user).order_by('date')
        gem_list = list(gems.values('was_liked', 'was_saved', 'track_popularity', 'date', 'track_id'))
        gem_total = len(gem_list)

        if gem_total == 0:
            return JsonResponse({'message': 'No gems yet'})

        gem_liked = sum(1 for g in gem_list if g['was_liked'] is True)
        gem_disliked = sum(1 for g in gem_list if g['was_liked'] is False)
        # Ratio 0..1 (MetricsStrip multiplies by 100 for display)
        gem_acceptance_rate = gem_liked / gem_total
        # compound_hit_rate: (was_liked=True OR was_saved=True) / total (D-12)
        # None counts as a miss — identity check ensures None != True (D-13)
        compound_hits = sum(1 for g in gem_list if g['was_liked'] is True or g['was_saved'] is True)
        compound_hit_rate = compound_hits / gem_total

        avg_pop = gems.aggregate(avg=Avg('track_popularity'))['avg'] or 0
        # hidden_gem_rate uses DailyGem.track_popularity, NOT RecommendationLog.was_novel (Pitfall 4)
        hidden_gem_rate = round(
            gems.filter(track_popularity__lt=40).count() / gem_total, 4
        )

        total_recommended = RecommendationLog.objects.filter(user=user).count()
        # novel_track_rate: was_novel is always True (Pitfall 4); reuse hidden_gem_rate
        novel_track_rate = hidden_gem_rate

        # taste_vector → top 10 genres normalized to percentage (D-07)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        taste_vector = profile.data.get('taste_vector', {})
        sorted_genres = sorted(taste_vector.items(), key=lambda x: x[1], reverse=True)
        top_genres = [g for g, _ in sorted_genres[:10]]
        total_counts = sum(c for _, c in sorted_genres[:10]) or 1
        top_genres_pct = [
            {'genre': g, 'pct': round(c / total_counts * 100, 1)}
            for g, c in sorted_genres[:10]
        ]

        # improvement_story: first 7 vs last 7 gems by like-rate (D-04)
        if gem_total < 2:
            improvement_story = {'first_7_rate': None, 'last_7_rate': None, 'delta': None}
        else:
            first_7 = gem_list[:7]
            last_7 = gem_list[-7:]
            f7_liked = sum(1 for g in first_7 if g['was_liked'] is True)
            l7_liked = sum(1 for g in last_7 if g['was_liked'] is True)
            first_7_rate = round(f7_liked / len(first_7) * 100)
            last_7_rate = round(l7_liked / len(last_7) * 100)
            delta = last_7_rate - first_7_rate
            improvement_story = {
                'first_7_rate': first_7_rate,
                'last_7_rate': last_7_rate,
                'delta': delta,
            }

        # diversity_score: mean pairwise Jaccard on DailyGem Track.genres (D-09, D-10, D-11)
        track_ids = [g['track_id'] for g in gem_list]
        track_genres_map = {
            t['id']: t['genres']
            for t in Track.objects.filter(id__in=track_ids).values('id', 'genres')
        }
        genre_lists = [track_genres_map.get(tid, []) for tid in track_ids]
        nonempty = [g for g in genre_lists if g]
        if len(nonempty) < 2:
            diversity_score = None
        else:
            sample = nonempty[-50:]  # cap at 50 most recent to avoid O(n²) blowup
            pairs = list(combinations(sample, 2))
            distances = [_jaccard_distance(a, b) for a, b in pairs]
            diversity_score = round(sum(distances) / len(distances), 4)

        return JsonResponse({
            'total_recommended': total_recommended,
            'avg_popularity': round(avg_pop),
            'novel_track_rate': novel_track_rate,
            'hidden_gem_rate': hidden_gem_rate,
            'gem_total': gem_total,
            'gem_liked': gem_liked,
            'gem_disliked': gem_disliked,
            'gem_acceptance_rate': gem_acceptance_rate,
            'compound_hit_rate': compound_hit_rate,
            'top_genres': top_genres,
            'top_genres_pct': top_genres_pct,
            'improvement_story': improvement_story,
            'diversity_score': diversity_score,
        })
    except Exception as e:
        logger.error(f"Error getting recommendation metrics: {str(e)}")
        return JsonResponse({'error': 'Failed to get recommendation metrics'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_trend(request):
    """
    Return rolling 7-day like-rate trend data for the authenticated user.

    For each distinct DailyGem date, compute like-rate across the 7-day window
    ending on that date. Returns {'data': []} with a message when fewer than 2
    dates exist (D-03, D-08).
    """
    try:
        user = request.user
        gems = list(
            DailyGem.objects.filter(user=user)
            .order_by('date')
            .values('date', 'was_liked')
        )
        dates = sorted(set(g['date'] for g in gems))
        data_points = []
        for d in dates:
            window_start = d - timedelta(days=6)
            window = [g for g in gems if window_start <= g['date'] <= d]
            liked = sum(1 for g in window if g['was_liked'] is True)
            total = len(window)
            like_rate = round((liked / total) * 100, 1) if total > 0 else 0.0
            data_points.append({'date': str(d), 'like_rate': like_rate})
        if len(data_points) < 2:
            return JsonResponse({'data': [], 'message': 'Not enough data'})
        return JsonResponse({'data': data_points})
    except Exception as e:
        logger.error(f"Error getting recommendation trend: {str(e)}")
        return JsonResponse({'error': 'Failed to get recommendation trend'}, status=500)


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
        try:
            spotify_token = SpotifyToken.objects.get(user=request.user)
        except SpotifyToken.DoesNotExist:
            return JsonResponse({'error': 'Spotify token not found'}, status=404)
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
            from apps.recommendations.personalization_engine import PersonalizationEngine
            personalization_engine = PersonalizationEngine(request.user)
            personalization_engine.remove_feedback_learning(track.spotify_id)
            
            # Also update hybrid profile
            hybrid_engine = HybridRecommendationEngine(request.user)
            hybrid_engine.remove_feedback(track.spotify_id)

            # Bug 3 fix (Phase 1): clear RecommendationLog.liked on unlike so metrics
            # queries (logs.filter(liked=True).count()) reflect the unrated state.
            log = RecommendationLog.objects.filter(
                user=request.user, track=track
            ).order_by('-recommended_at').first()
            if log:
                log.liked = None
                log.save(update_fields=['liked'])

            # Sync DailyGem.was_liked: clear it on unlike so today's gem reflects state.
            gem = DailyGem.objects.filter(
                user=request.user, date=timezone.localdate(), track=track
            ).first()
            if gem:
                gem.was_liked = None
                gem.save(update_fields=['was_liked'])

            return JsonResponse({'status': 'success', 'action': 'removed'})
        else:
            # If a prior LIKE exists and we're replacing it (e.g. LIKE → DISLIKE),
            # undo the LIKE's taste-vector increment before applying the new feedback.
            prior_like = UserFeedback.objects.filter(
                user=request.user, track=track, feedback_type='LIKE'
            ).first()

            # Create or update feedback entry — update_or_create prevents
            # IntegrityError from unique_together(user, track) when the same
            # user submits different feedback types for the same track.
            feedback, _ = UserFeedback.objects.update_or_create(
                user=request.user,
                track=track,
                defaults={'feedback_type': feedback_type, 'track_features': {}}
            )

            from apps.recommendations.personalization_engine import PersonalizationEngine
            personalization_engine = PersonalizationEngine(request.user)

            if prior_like and feedback_type != 'LIKE':
                personalization_engine.remove_feedback_learning(track.spotify_id)

            # Update recommendations using the enhanced personalization engine
            personalization_engine.apply_feedback_learning(feedback)
            
            # Also update hybrid profile
            hybrid_engine = HybridRecommendationEngine(request.user)
            track_info = {
                'artist': track.artist,
                'name': track.name,
                'album': track.album
            }
            hybrid_engine.add_feedback(track.spotify_id, feedback.feedback_type, track_info)

            # DISLIKE → auto-add track genres to AI avoidance list so the scoring
            # filter applies even without a natural-language text submission.
            if feedback_type == 'DISLIKE' and track.genres:
                dislike_interpretation = {
                    'genre_preference': 'avoid_genre',
                    'specific_genres': track.genres[:3],
                    'confidence': 0.85,
                }
                hybrid_engine.add_ai_feedback(dislike_interpretation, {
                    'name': track.name,
                    'artist': track.artist,
                    'genres': track.genres,
                })

            logger.info(f"Feedback processed: {feedback.feedback_type} for track {track.name}")

            # Bug 3 fix (Phase 1): write RecommendationLog.liked so success metrics
            # (logs.filter(liked=True).count()) become non-zero. Maps:
            #   feedback_type == 'LIKE'    -> liked = True
            #   feedback_type == 'DISLIKE' -> liked = False
            log = RecommendationLog.objects.filter(
                user=request.user, track=track
            ).order_by('-recommended_at').first()
            if log:
                log.liked = (feedback_type == 'LIKE')
                log.save(update_fields=['liked'])

            # Sync DailyGem.was_liked so today's gem reflects LIKE/DISLIKE feedback.
            if feedback_type in ('LIKE', 'DISLIKE'):
                gem = DailyGem.objects.filter(
                    user=request.user, date=timezone.localdate(), track=track
                ).first()
                if gem:
                    gem.was_liked = (feedback_type == 'LIKE')
                    gem.save(update_fields=['was_liked'])

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
            track, _ = Track.objects.get_or_create(
                spotify_id=track_id,
                defaults={'name': '', 'artist': '', 'album': ''}
            )
            track_info = {
                'name': track.name,
                'artist': track.artist,
                'album': track.album,
                'genres': track.genres or [],
            }

        # Guard: track is required (AIFeedback.track is non-nullable)
        if track is None:
            return JsonResponse(
                {'error': 'track_id is required'},
                status=400
            )

        # Initialize AI feedback interpreter
        interpreter = get_feedback_interpreter()

        try:
            # Interpret the feedback
            interpretation = interpreter.interpret_feedback(feedback_text, track_info)

            # If user said "this genre" but AI didn't name specific genres, inject the
            # current track's genres so the avoidance filter has something to match on.
            if (
                interpretation.get('genre_preference') == 'avoid_genre'
                and not interpretation.get('specific_genres')
                and track_info
                and track_info.get('genres')
            ):
                interpretation['specific_genres'] = track_info['genres'][:3]

            # Store the AI feedback
            ai_feedback = AIFeedback.objects.create(
                user=request.user,
                track=track,
                original_feedback=feedback_text,
                ai_interpretation=interpretation,
                confidence_score=interpretation.get('confidence', 0.0)
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

def get_user_name(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    """Get user's name using Spotipy"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        me = sp.me()
        return JsonResponse({
            'user_name': {
                'display_name': me.get('display_name', ''),
                'images': me.get('images', []),
            }
        })

    except SpotifyException as e:
        logger.error(f"Spotify API error in get_user_name: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_user_name: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_track_to_liked(request):
    """Add a track to the user's Spotify liked songs library."""
    try:
        track_id = request.data.get("track_id")
        if not track_id:
            return JsonResponse({'error': 'track_id is required'}, status=400)

        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)

        sp = get_spotipy_client(spotify_token.access_token)
        sp.current_user_saved_tracks_add([track_id])

        try:
            today = timezone.localdate()
            DailyGem.objects.filter(
                user=request.user, date=today, track__spotify_id=track_id
            ).update(was_saved=True)
        except Exception:
            pass

        return JsonResponse({'message': "all good"})

    except SpotifyException as e:
        logger.error(f"Spotify API error in add_track_to_liked: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in add_track_to_liked: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@login_required
def get_artist_details(request, artist_id):
    """Get detailed information about a specific artist"""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if spotify_token.is_expired():
            spotify_token = refresh_spotify_token(spotify_token)
        
        sp = get_spotipy_client(spotify_token.access_token)
        
        # Get detailed artist information
        artist = sp.artist(artist_id)
        
        # Get artist's top tracks (globally popular)
        top_tracks = sp.artist_top_tracks(artist_id, country='US')
        
        # Get latest albums
        albums = sp.artist_albums(
            artist_id, 
            album_type='album,single',
            limit=1,  # Only get the latest release
            country='US'
        )
        
        # Get user's recently played tracks and filter by this artist
        recently_played = sp.current_user_recently_played(limit=50)
        recent_tracks_by_artist = [
            track for track in recently_played['items'] 
            if track['track']['artists'][0]['id'] == artist_id
        ][:5]  # Top 5 most recently played by this artist
        
        # Get user's top tracks and filter by this artist
        user_top_tracks = sp.current_user_top_tracks(limit=50, time_range='medium_term')
        top_tracks_by_artist = [
            track for track in user_top_tracks['items'] 
            if track['artists'][0]['id'] == artist_id
        ][:5]  # Top 5 from user's top tracks
        
        # Get user's liked songs and filter by this artist
        liked_songs = sp.current_user_saved_tracks(limit=50)
        liked_tracks_by_artist = [
            track for track in liked_songs['items'] 
            if track['track']['artists'][0]['id'] == artist_id
        ][:5]  # Top 5 liked tracks by this artist
        
        # Combine and deduplicate tracks, prioritizing top tracks first
        combined_tracks = []
        seen_track_ids = set()
        
        # Add top tracks first (highest priority)
        for track in top_tracks_by_artist:
            if track['id'] not in seen_track_ids:
                combined_tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'album': track['album']['name'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'preview_url': track['preview_url'],
                    'external_urls': track['external_urls'],
                    'source': 'top_tracks'
                })
                seen_track_ids.add(track['id'])
        
        # Add recent tracks (second priority, only if not already included)
        for track in recent_tracks_by_artist:
            if track['track']['id'] not in seen_track_ids and len(combined_tracks) < 5:
                combined_tracks.append({
                    'id': track['track']['id'],
                    'name': track['track']['name'],
                    'album': track['track']['album']['name'],
                    'image': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None,
                    'preview_url': track['track']['preview_url'],
                    'external_urls': track['track']['external_urls'],
                    'source': 'recent_tracks'
                })
                seen_track_ids.add(track['track']['id'])
        
        # Add liked tracks (third priority, only if not already included)
        for track in liked_tracks_by_artist:
            if track['track']['id'] not in seen_track_ids and len(combined_tracks) < 5:
                combined_tracks.append({
                    'id': track['track']['id'],
                    'name': track['track']['name'],
                    'album': track['track']['album']['name'],
                    'image': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None,
                    'preview_url': track['track']['preview_url'],
                    'external_urls': track['track']['external_urls'],
                    'source': 'liked_songs'
                })
                seen_track_ids.add(track['track']['id'])
        
        # If we still don't have 5 tracks, add some from artist's albums as fallback (fourth priority)
        if len(combined_tracks) < 5:
            try:
                albums = sp.artist_albums(artist_id, album_type='album,single', limit=5)
                for album in albums['items']:
                    album_tracks = sp.album_tracks(album['id'])
                    for track in album_tracks['items']:
                        if track['id'] not in seen_track_ids and len(combined_tracks) < 5:
                            combined_tracks.append({
                                'id': track['id'],
                                'name': track['name'],
                                'album': album['name'],
                                'image': album['images'][0]['url'] if album['images'] else None,
                                'preview_url': track['preview_url'],
                                'external_urls': track['external_urls'],
                                'source': 'artist_albums'
                            })
                            seen_track_ids.add(track['id'])
                        if len(combined_tracks) >= 5:
                            break
                    if len(combined_tracks) >= 5:
                        break
            except Exception as e:
                logger.warning(f"Could not get fallback tracks for artist {artist_id}: {str(e)}")
        
        user_tracks_by_artist = combined_tracks[:5]  # Ensure exactly 5 tracks
        
        artist_data = {
            'id': artist['id'],
            'name': artist['name'],
            'genres': artist['genres'],
            'popularity': artist['popularity'],
            'images': artist['images'],
            'followers': artist['followers']['total'],
            'external_urls': artist['external_urls'],
            'bio': None,  # Spotify doesn't provide bio in artist endpoint
            'top_tracks': [{
                'id': track['id'],
                'name': track['name'],
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'preview_url': track['preview_url'],
                'external_urls': track['external_urls']
            } for track in top_tracks['tracks'][:5]],  # Top 5 tracks
            'latest_album': {
                'id': albums['items'][0]['id'],
                'name': albums['items'][0]['name'],
                'type': albums['items'][0]['album_type'],
                'release_date': albums['items'][0]['release_date'],
                'image': albums['items'][0]['images'][0]['url'] if albums['items'][0]['images'] else None,
                'total_tracks': albums['items'][0]['total_tracks']
            } if albums['items'] else None,  # Latest album (single object)
            'user_top_tracks': [{
                'id': track['id'],
                'name': track['name'],
                'album': track['album'],
                'image': track['image'],
                'preview_url': track['preview_url'],
                'external_urls': track['external_urls'],
                'source': track['source']
            } for track in user_tracks_by_artist]
        }
        
        logger.info(f"Retrieved detailed info for artist: {artist['name']}")

        return JsonResponse(artist_data)

    except SpotifyException as e:
        logger.error(f"Spotify API error in get_artist_details: {str(e)}")
        return JsonResponse({'error': 'Spotify API error'}, status=getattr(e, 'http_status', 502) or 502)
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'error': 'Spotify token not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_artist_details: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


def _build_gem_explanation(breakdown: dict, track_name: str, artist_name: str, source: str) -> str:
    """
    Build a deterministic, human-readable explanation for why a gem was picked.

    Pure function: no external calls, no logging, no exceptions on any reasonable input.
    Returns one of four sentence shapes based on the dominant scoring component, or a
    neutral fallback when the breakdown is empty or all-zero.

    Args:
        breakdown:    score_breakdown dict from _score_recommendations (may be empty)
        track_name:   Spotify track name (unused in current sentences, retained for signature parity)
        artist_name:  Spotify artist name (used in feedback_multiplier sentence)
        source:       Discovery strategy label (e.g. 'playlist mining', 'artist network')

    Returns:
        Human-readable explanation string.
    """
    # --- Guard: empty or all-zero breakdown → neutral fallback -----------------
    if not breakdown:
        return 'Picked based on your listening patterns'

    genre_sim = breakdown.get('genre_sim', 0.0)
    novelty = breakdown.get('novelty', 0.0)
    feedback_multiplier = breakdown.get('feedback_multiplier', 0.0)

    if max(genre_sim, novelty, feedback_multiplier) == 0.0:
        return 'Picked based on your listening patterns'

    # --- Source string ---------------------------------------------------------
    source_str = f'via {source}' if source else 'via discovery'

    # --- Dominant component ---------------------------------------------------
    components = {
        'genre_sim': genre_sim,
        'novelty': novelty,
        'feedback_multiplier': feedback_multiplier,
    }
    dominant = max(components, key=components.get)

    # --- Sentence shapes (D-02 / D-03 / D-04) ---------------------------------
    if dominant == 'genre_sim':
        pct = round(genre_sim * 100)
        return (
            f'Matches your listening taste — genre similarity: {pct}%, '
            f'discovered {source_str}'
        )
    elif dominant == 'novelty':
        return (
            f'A hidden gem — low popularity score makes it a genuine discovery, '
            f'found {source_str}'
        )
    else:  # feedback_multiplier
        return (
            f"You've liked {artist_name} before — that feedback boosted this pick, "
            f'sourced {source_str}'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_gem(request):
    """
    Return today's daily gem for the authenticated user.

    Cached branch: if a DailyGem row already exists for today, return it immediately
    with score_breakdown: {} (we don't re-score cached gems).

    Fresh branch: generate recommendations via HybridRecommendationEngine, pick the
    top-scored candidate, persist it as a DailyGem row, and return the response with
    score_breakdown populated from _score_recommendations().

    Authentication: @permission_classes([IsAuthenticated]) — unauthenticated requests
    receive 403 (DRF default), not 404. (T-03-11 mitigation)
    """
    try:
        today = timezone.localdate()
        force_new = request.GET.get('force_new', 'false').lower() == 'true'

        # Capture the previous gem's track ID before deletion so we can hard-exclude
        # it from the new candidate pool — prevents the same song being returned twice.
        previous_gem_track_id = None
        if force_new:
            prev_gem = DailyGem.objects.filter(user=request.user, date=today).select_related('track').first()
            if prev_gem:
                previous_gem_track_id = prev_gem.track.spotify_id
            DailyGem.objects.filter(user=request.user, date=today).delete()

        # --- Cached branch ---------------------------------------------------
        if not force_new:
            try:
                gem = DailyGem.objects.get(user=request.user, date=today)
                track = gem.track
                return JsonResponse({
                    'track': {
                        'id': track.spotify_id,
                        'name': track.name,
                        'artist': track.artist,
                        'album': track.album,
                        'popularity': track.popularity if hasattr(track, 'popularity') else 0,
                        'image_url': gem.image_url or None,
                        'preview_url': gem.preview_url or None,
                    },
                    'explanation': gem.explanation,
                    'date': str(gem.date),
                    'cached': True,
                    'score_breakdown': gem.score_breakdown,
                })
            except DailyGem.DoesNotExist:
                pass  # Fall through to fresh branch

        # --- Fresh branch ----------------------------------------------------
        try:
            spotify_token = SpotifyToken.objects.get(user=request.user)
            if spotify_token.is_expired():
                spotify_token = refresh_spotify_token(spotify_token)
        except SpotifyToken.DoesNotExist:
            return JsonResponse({'error': 'Spotify token not found'}, status=404)

        engine = HybridRecommendationEngine(request.user)
        exclude = {previous_gem_track_id} if previous_gem_track_id else None
        candidates = engine.get_recommendations(limit=10, force_fresh=force_new, exclude_ids=exclude)

        if not candidates:
            return JsonResponse({'error': 'No recommendations available'}, status=503)

        # Top candidate (already sorted descending by _score_recommendations)
        gem_data = candidates[0]

        # Persist Track to DB
        track_obj, _ = Track.objects.get_or_create(
            spotify_id=gem_data['id'],
            defaults={
                'name': gem_data.get('name', ''),
                'artist': gem_data.get('artist', ''),
                'album': gem_data.get('album', ''),
            },
        )

        # Extract score fields from the top candidate
        breakdown = gem_data.get('score_breakdown', {})
        taste_snapshot = engine.profile.data.get('taste_vector', {})

        # Persist DailyGem row (unique_together user+date enforces one gem per day)
        # All 4 score fields are written in a single DB write as part of defaults (D-10).
        gem, created = DailyGem.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={
                'track': track_obj,
                'explanation': _build_gem_explanation(
                    breakdown,
                    gem_data.get('name', ''),
                    gem_data.get('artist', ''),
                    breakdown.get('source', ''),
                ),
                'score_breakdown': breakdown,
                'score_total': gem_data.get('score', None),
                'taste_vector_snapshot': taste_snapshot,
                'image_url': gem_data.get('image_url') or '',
                'preview_url': gem_data.get('preview_url') or '',
                'track_popularity': gem_data.get('popularity', 0),
            },
        )
        # Log to RecommendationLog so this track stays in _get_persistent_exclusion_set()
        # even after the DailyGem row is deleted by a subsequent force_new request.
        if created:
            try:
                RecommendationLog.log_recommendation(
                    request.user, track_obj, source=gem_data.get('source', 'daily_gem')
                )
            except Exception as log_err:
                logger.error(f"Error logging daily gem to RecommendationLog: {log_err}")

        if not created:
            # Race condition: another request created the gem between our DoesNotExist
            # and get_or_create — return the cached one.
            track = gem.track
            return JsonResponse({
                'track': {
                    'id': track.spotify_id,
                    'name': track.name,
                    'artist': track.artist,
                    'album': track.album,
                    'popularity': track.popularity if hasattr(track, 'popularity') else 0,
                    'image_url': gem.image_url or None,
                    'preview_url': gem.preview_url or None,
                },
                'explanation': gem.explanation,
                'date': str(gem.date),
                'cached': True,
                'score_breakdown': gem.score_breakdown,
            })

        return JsonResponse({
            'track': {
                'id': gem_data.get('id', ''),
                'name': gem_data.get('name', ''),
                'artist': gem_data.get('artist', ''),
                'album': gem_data.get('album', ''),
                'popularity': gem_data.get('popularity', 0),
                'image_url': gem_data.get('image_url'),
                'preview_url': gem_data.get('preview_url'),
            },
            'explanation': gem.explanation,
            'date': str(today),
            'cached': False,
            'score_breakdown': gem_data.get('score_breakdown', {}),
        })

    except Exception as e:
        logger.error(f"Error in get_daily_gem: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Failed to generate daily gem'}, status=500)


@api_view(['POST'])
def logout_view(request):
    """Clear Django session and log the user out."""
    logout(request)
    return JsonResponse({'status': 'ok'})
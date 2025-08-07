"""
Hybrid Recommendation Engine - Combines multiple strategies for better recommendations

This engine implements a sophisticated recommendation system that:
1. Uses playlist mining to find hidden gems
2. Leverages artist networks for discovery
3. Applies contextual analysis for time/mood-based recommendations
4. Learns from user feedback to improve over time
5. Respects Spotify API rate limits and terms of service
"""

import logging
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from datetime import timedelta
import json

from .models import UserProfile, Track, UserFeedback
from .utils import rate_limit_monitor, get_spotipy_client
from .track_discovery_engine import TrackDiscoveryEngine

logger = logging.getLogger(__name__)

class HybridRecommendationEngine:
    """
    Hybrid recommendation engine that combines multiple strategies.
    Uses user profiles for efficient, personalized recommendations.
    """
    
    def __init__(self, user):
        self.user = user
        self.profile = self._get_or_create_profile()
        self.rate_limit_monitor = rate_limit_monitor
    
    def _get_or_create_profile(self) -> UserProfile:
        """Get existing profile or create new one"""
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        
        if created:
            logger.info(f"Created new profile for user {self.user.id}")
            # Initialize with default structure
            profile.data = {
                'base_data': {},
                'preferences': {
                    'liked_artists': [],
                    'disliked_artists': [],
                    'feedback_history': []
                },
                'recommendation_weights': {
                    'playlist_mining': 0.3,
                    'artist_network': 0.25,
                    'contextual': 0.2,
                    'popularity': 0.15,
                    'feedback': 0.1
                },
                'errors': [],
                'partial_data': False
            }
            profile.save()
        
        return profile
    
    def get_recommendations(self, limit=20) -> List[Dict]:
        """
        Get personalized recommendations using hybrid approach.
        Combines multiple strategies based on user profile.
        """
        try:
            logger.info(f"Getting hybrid recommendations for user {self.user.id}")
            
            # Check if profile needs updating or is empty
            if self.profile.needs_update() or not self._has_base_data():
                logger.info("Profile needs updating or is empty, refreshing data...")
                self._update_profile_data()
            
            # Get recommendations from multiple sources
            all_recommendations = []
            
            # Strategy 1: Playlist Mining
            if self._check_rate_limit():
                playlist_recs = self._get_playlist_recommendations(limit // 3)
                all_recommendations.extend(playlist_recs)
                logger.info(f"Playlist mining found {len(playlist_recs)} recommendations")
            
            # Strategy 2: Artist Network
            if self._check_rate_limit():
                artist_recs = self._get_artist_network_recommendations(limit // 3)
                all_recommendations.extend(artist_recs)
                logger.info(f"Artist network found {len(artist_recs)} recommendations")
            
            # Strategy 3: Contextual Recommendations
            if self._check_rate_limit():
                contextual_recs = self._get_contextual_recommendations(limit // 3)
                all_recommendations.extend(contextual_recs)
                logger.info(f"Contextual analysis found {len(contextual_recs)} recommendations")
            
            # If no recommendations from hybrid strategies, use fallback
            if not all_recommendations:
                logger.info("No hybrid recommendations found, using fallback...")
                return self._get_fallback_recommendations(limit)
            
            # Remove duplicates and score
            unique_recommendations = self._remove_duplicates(all_recommendations)
            scored_recommendations = self._score_recommendations(unique_recommendations)
            
            # Return top recommendations
            final_recommendations = scored_recommendations[:limit]
            
            logger.info(f"Generated {len(final_recommendations)} hybrid recommendations")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error in hybrid recommendations: {str(e)}")
            # Fallback to basic track discovery
            return self._get_fallback_recommendations(limit)
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make API calls"""
        return self.rate_limit_monitor.check_rate_limit()
    
    def _has_base_data(self) -> bool:
        """Check if profile has base data"""
        base_data = self.profile.data.get('base_data', {})
        return bool(base_data.get('top_artists') or base_data.get('saved_tracks') or base_data.get('playlists'))
    
    def _update_profile_data(self):
        """Update user profile with fresh data from Spotify"""
        try:
            from .models import SpotifyToken
            spotify_token = SpotifyToken.objects.filter(user=self.user).first()
            if not spotify_token or spotify_token.is_expired():
                logger.error("No valid Spotify token available for profile update")
                return
            
            sp = get_spotipy_client(spotify_token.access_token)
            
            # Update base data with error handling
            self._update_top_artists(sp)
            self._update_saved_tracks(sp)
            self._update_playlists(sp)
            self._update_listening_patterns(sp)
            
            # Mark as updated
            self.profile.save()
            logger.info(f"Updated profile for user {self.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            self.profile.data['errors'].append({
                'type': 'profile_update_failure',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            })
            self.profile.save()
            
            # If profile update fails, try to get recommendations anyway
            logger.info("Profile update failed, attempting to get recommendations with existing data...")
    
    def _update_top_artists(self, sp):
        """Update user's top artists"""
        try:
            if not self._check_rate_limit():
                return
            
            top_artists = sp.current_user_top_artists(limit=20)
            self.profile.data['base_data']['top_artists'] = [
                {
                    'id': artist['id'],
                    'name': artist['name'],
                    'genres': artist['genres'],
                    'popularity': artist['popularity']
                }
                for artist in top_artists['items']
            ]
        except Exception as e:
            logger.error(f"Error updating top artists: {str(e)}")
            self._add_error('top_artists', 'api_failure', str(e))
    
    def _update_saved_tracks(self, sp):
        """Update user's saved tracks"""
        try:
            if not self._check_rate_limit():
                return
            
            saved_tracks = sp.current_user_saved_tracks(limit=50)
            self.profile.data['base_data']['saved_tracks'] = [
                {
                    'id': item['track']['id'],
                    'name': item['track']['name'],
                    'artist': item['track']['artists'][0]['name'],
                    'artist_id': item['track']['artists'][0]['id'],
                    'added_at': item['added_at']
                }
                for item in saved_tracks['items']
            ]
        except Exception as e:
            logger.error(f"Error updating saved tracks: {str(e)}")
            self._add_error('saved_tracks', 'api_failure', str(e))
    
    def _update_playlists(self, sp):
        """Update user's playlists"""
        try:
            if not self._check_rate_limit():
                return
            
            playlists = sp.current_user_playlists(limit=20)
            self.profile.data['base_data']['playlists'] = [
                {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'track_count': playlist['tracks']['total'],
                    'owner': playlist['owner']['id']
                }
                for playlist in playlists['items']
            ]
        except Exception as e:
            logger.error(f"Error updating playlists: {str(e)}")
            self._add_error('playlists', 'api_failure', str(e))
    
    def _update_listening_patterns(self, sp):
        """Update listening patterns"""
        try:
            if not self._check_rate_limit():
                return
            
            recent_tracks = sp.current_user_recently_played(limit=50)
            
            # Analyze patterns by time of day
            patterns = {'morning': [], 'afternoon': [], 'evening': [], 'night': []}
            
            for item in recent_tracks['items']:
                played_at = item['played_at']
                hour = timezone.datetime.fromisoformat(played_at.replace('Z', '+00:00')).hour
                
                if 6 <= hour < 12:
                    patterns['morning'].append(item['track']['id'])
                elif 12 <= hour < 17:
                    patterns['afternoon'].append(item['track']['id'])
                elif 17 <= hour < 22:
                    patterns['evening'].append(item['track']['id'])
                else:
                    patterns['night'].append(item['track']['id'])
            
            self.profile.data['base_data']['listening_patterns'] = patterns
            
        except Exception as e:
            logger.error(f"Error updating listening patterns: {str(e)}")
            self._add_error('listening_patterns', 'api_failure', str(e))
    
    def _add_error(self, endpoint: str, error_type: str, error_message: str):
        """Add error to profile"""
        self.profile.data['errors'].append({
            'type': error_type,
            'endpoint': endpoint,
            'error': error_message,
            'timestamp': timezone.now().isoformat()
        })
        self.profile.data['partial_data'] = True
    
    def _get_playlist_recommendations(self, limit: int) -> List[Dict]:
        """Get recommendations by mining user's playlists"""
        recommendations = []
        
        try:
            playlists = self.profile.data['base_data'].get('playlists', [])
            saved_track_ids = {
                track['id'] for track in self.profile.data['base_data'].get('saved_tracks', [])
            }
            
            for playlist in playlists[:5]:  # Limit to 5 playlists to avoid rate limits
                if not self._check_rate_limit():
                    break
                
                try:
                    # Get playlist tracks
                    sp = self._get_spotify_client()
                    if not sp:
                        continue
                    
                    playlist_tracks = sp.playlist_tracks(playlist['id'], limit=20)
                    
                    for item in playlist_tracks['items']:
                        track = item['track']
                        if track['id'] not in saved_track_ids:  # Don't recommend already saved tracks
                            recommendations.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'album': track['album']['name'],
                                'preview_url': track.get('preview_url'),
                                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                'source': 'playlist_mining',
                                'playlist_name': playlist['name'],
                                'score': 0.0  # Will be calculated later
                            })
                            
                            if len(recommendations) >= limit:
                                break
                    
                except Exception as e:
                    logger.warning(f"Error getting playlist {playlist['id']}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in playlist mining: {str(e)}")
        
        return recommendations[:limit]
    
    def _get_artist_network_recommendations(self, limit: int) -> List[Dict]:
        """Get recommendations through artist network"""
        recommendations = []
        
        try:
            top_artists = self.profile.data['base_data'].get('top_artists', [])
            liked_artists = self.profile.data['preferences'].get('liked_artists', [])
            disliked_artists = self.profile.data['preferences'].get('disliked_artists', [])
            
            # Combine top artists and liked artists
            all_artists = top_artists + [{'name': artist} for artist in liked_artists]
            
            for artist in all_artists[:3]:  # Limit to avoid rate limits
                if not self._check_rate_limit():
                    break
                
                try:
                    sp = self._get_spotify_client()
                    if not sp:
                        continue
                    
                    # Get artist's top tracks
                    if 'id' in artist:
                        top_tracks = sp.artist_top_tracks(artist['id'], country='US')
                        
                        for track in top_tracks['tracks'][:3]:
                            if track['artists'][0]['name'] not in disliked_artists:
                                recommendations.append({
                                    'id': track['id'],
                                    'name': track['name'],
                                    'artist': track['artists'][0]['name'],
                                    'album': track['album']['name'],
                                    'preview_url': track.get('preview_url'),
                                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                    'source': 'artist_network',
                                    'artist_name': artist['name'],
                                    'score': 0.0
                                })
                                
                                if len(recommendations) >= limit:
                                    break
                    
                except Exception as e:
                    logger.warning(f"Error getting artist {artist.get('name', 'unknown')}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in artist network: {str(e)}")
        
        return recommendations[:limit]
    
    def _get_contextual_recommendations(self, limit: int) -> List[Dict]:
        """Get contextual recommendations based on time/mood"""
        recommendations = []
        
        try:
            current_hour = timezone.now().hour
            patterns = self.profile.data['base_data'].get('listening_patterns', {})
            
            # Determine current time period
            if 6 <= current_hour < 12:
                time_period = 'morning'
            elif 12 <= current_hour < 17:
                time_period = 'afternoon'
            elif 17 <= current_hour < 22:
                time_period = 'evening'
            else:
                time_period = 'night'
            
            # Get tracks from current time period
            track_ids = patterns.get(time_period, [])
            
            if track_ids and self._check_rate_limit():
                try:
                    sp = self._get_spotify_client()
                    if sp:
                        # Get track details
                        tracks = sp.tracks(track_ids[:5])  # Limit to 5 tracks
                        
                        for track in tracks['tracks']:
                            recommendations.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'album': track['album']['name'],
                                'preview_url': track.get('preview_url'),
                                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                'source': 'contextual',
                                'time_period': time_period,
                                'score': 0.0
                            })
                            
                            if len(recommendations) >= limit:
                                break
                                
                except Exception as e:
                    logger.warning(f"Error getting contextual tracks: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in contextual recommendations: {str(e)}")
        
        return recommendations[:limit]
    
    def _get_spotify_client(self):
        """Get Spotify client with error handling"""
        try:
            from .models import SpotifyToken
            spotify_token = SpotifyToken.objects.filter(user=self.user).first()
            if not spotify_token or spotify_token.is_expired():
                return None
            
            return get_spotipy_client(spotify_token.access_token)
        except Exception as e:
            logger.error(f"Error getting Spotify client: {str(e)}")
            return None
    
    def _remove_duplicates(self, recommendations: List[Dict]) -> List[Dict]:
        """Remove duplicate tracks based on track ID"""
        seen_ids = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Score recommendations based on user profile and preferences"""
        weights = self.profile.get_recommendation_weights()
        liked_artists = self.profile.data['preferences'].get('liked_artists', [])
        disliked_artists = self.profile.data['preferences'].get('disliked_artists', [])
        
        for rec in recommendations:
            score = 0.0
            
            # Base score from source
            source_weight = weights.get(rec['source'], 0.1)
            score += source_weight
            
            # Artist preference bonus
            if rec['artist'] in liked_artists:
                score += weights['feedback'] * 2  # Double the feedback weight
            elif rec['artist'] in disliked_artists:
                score -= weights['feedback'] * 3  # Heavy penalty for disliked artists
            
            # Contextual bonus
            if rec['source'] == 'contextual':
                score += weights['contextual'] * 0.5
            
            # Playlist mining bonus (hidden gems)
            if rec['source'] == 'playlist_mining':
                score += weights['playlist_mining'] * 0.3
            
            rec['score'] = max(0.0, score)  # Ensure non-negative score
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations
    
    def _get_fallback_recommendations(self, limit: int) -> List[Dict]:
        """Fallback to basic track discovery if hybrid approach fails"""
        try:
            logger.info("Using fallback track discovery engine...")
            discovery_engine = TrackDiscoveryEngine(self.user)
            sp = self._get_spotify_client()
            if sp:
                fallback_recs = discovery_engine.get_personalized_recommendations(sp, limit)
                logger.info(f"Fallback engine found {len(fallback_recs)} recommendations")
                return fallback_recs
            else:
                logger.error("No Spotify client available for fallback")
        except Exception as e:
            logger.error(f"Fallback recommendations also failed: {str(e)}")
        
        logger.warning("No recommendations available from any source")
        return []
    
    def add_feedback(self, track_id: str, feedback_type: str, track_info: Dict = None):
        """Add user feedback and update profile"""
        self.profile.add_feedback(track_id, feedback_type, track_info)
        logger.info(f"Added feedback: {feedback_type} for track {track_id}")
    
    def get_profile_summary(self) -> Dict:
        """Get summary of user profile"""
        return {
            'user_id': self.user.id,
            'profile_created': self.profile.created_at.isoformat(),
            'last_updated': self.profile.updated_at.isoformat(),
            'needs_update': self.profile.needs_update(),
            'base_data_keys': list(self.profile.data.get('base_data', {}).keys()),
            'preferences': {
                'liked_artists_count': len(self.profile.data.get('preferences', {}).get('liked_artists', [])),
                'feedback_count': len(self.profile.data.get('preferences', {}).get('feedback_history', []))
            },
            'recommendation_weights': self.profile.get_recommendation_weights(),
            'errors_count': len(self.profile.data.get('errors', [])),
            'partial_data': self.profile.data.get('partial_data', False)
        } 
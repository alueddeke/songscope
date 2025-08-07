"""
Track Discovery Engine - Alternative to Spotify Recommendations API

This engine builds personalized recommendations using:
1. User's top tracks
2. User's recently played
3. User's saved tracks
4. Similar artists/tracks from liked content
5. Rule-based filtering based on user feedback

This approach avoids the problematic Spotify recommendations API while still
providing personalized music discovery.
"""

from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
import random
from typing import Dict, List, Optional
from .models import UserFeedback, Track
from .personalization_engine import PersonalizationEngine
import logging

logger = logging.getLogger(__name__)

class TrackDiscoveryEngine:
    """
    Alternative recommendation engine that doesn't rely on Spotify's recommendations API.
    
    Instead, it builds recommendations from user data and applies personalization rules.
    """
    
    def __init__(self, user):
        self.user = user
        self.personalization_engine = PersonalizationEngine(user)
    
    def get_personalized_recommendations(self, sp_client, limit=20) -> List[Dict]:
        """
        Get personalized recommendations using user data instead of Spotify's API.
        
        Args:
            sp_client: Spotify client
            limit: Number of recommendations to return
            
        Returns:
            List of track dictionaries
        """
        try:
            logger.info(f"Getting personalized recommendations for user {self.user.id}")
            
            # Get user preferences for filtering
            user_preferences = self.personalization_engine.analyze_user_preferences()
            
            # Build recommendations from multiple sources
            recommendations = []
            
            # Source 1: User's top tracks (with variations)
            top_track_recommendations = self._get_top_track_variations(sp_client, limit//3)
            recommendations.extend(top_track_recommendations)
            
            # Source 2: Recently played with similar tracks
            recent_recommendations = self._get_recent_play_variations(sp_client, limit//3)
            recommendations.extend(recent_recommendations)
            
            # Source 3: Saved/liked tracks with similar content
            saved_recommendations = self._get_saved_track_variations(sp_client, limit//3)
            recommendations.extend(saved_recommendations)
            
            # Remove duplicates and limit
            unique_recommendations = self._remove_duplicates(recommendations)
            final_recommendations = unique_recommendations[:limit]
            
            logger.info(f"Generated {len(final_recommendations)} recommendations from user data")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error in get_personalized_recommendations: {str(e)}")
            return []
    
    def _get_top_track_variations(self, sp_client, limit: int) -> List[Dict]:
        """Get variations of user's top tracks."""
        try:
            # Get user's top tracks
            top_tracks = sp_client.current_user_top_tracks(limit=10)
            
            recommendations = []
            for track in top_tracks['items']:
                # Add the top track itself
                recommendations.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track.get('preview_url'),
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'source': 'top_tracks',
                    'popularity': track.get('popularity', 0)
                })
                
                # Get similar tracks by searching for the artist
                if len(recommendations) < limit:
                    similar_tracks = self._get_artist_tracks(sp_client, track['artists'][0]['id'], 2)
                    recommendations.extend(similar_tracks)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top track variations: {str(e)}")
            return []
    
    def _get_recent_play_variations(self, sp_client, limit: int) -> List[Dict]:
        """Get variations based on recently played tracks."""
        try:
            # Get recently played tracks
            recent_tracks = sp_client.current_user_recently_played(limit=10)
            
            recommendations = []
            for item in recent_tracks['items']:
                track = item['track']
                recommendations.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track.get('preview_url'),
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'source': 'recently_played',
                    'popularity': track.get('popularity', 0)
                })
                
                # Get tracks from the same album
                if len(recommendations) < limit:
                    album_tracks = self._get_album_tracks(sp_client, track['album']['id'], 2)
                    recommendations.extend(album_tracks)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent play variations: {str(e)}")
            return []
    
    def _get_saved_track_variations(self, sp_client, limit: int) -> List[Dict]:
        """Get variations based on saved/liked tracks."""
        try:
            # Get user's saved tracks
            saved_tracks = sp_client.current_user_saved_tracks(limit=10)
            
            recommendations = []
            for item in saved_tracks['items']:
                track = item['track']
                recommendations.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track.get('preview_url'),
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'source': 'saved_tracks',
                    'popularity': track.get('popularity', 0)
                })
                
                # Get related artists (but don't fail if this doesn't work)
                if len(recommendations) < limit:
                    try:
                        related_artists = self._get_related_artists(sp_client, track['artists'][0]['id'], 2)
                        recommendations.extend(related_artists)
                    except Exception as e:
                        logger.warning(f"Could not get related artists for {track['artists'][0]['name']}: {str(e)}")
                        continue
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting saved track variations: {str(e)}")
            return []
    
    def _get_artist_tracks(self, sp_client, artist_id: str, limit: int) -> List[Dict]:
        """Get popular tracks from an artist."""
        try:
            # Get artist's top tracks
            top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
            
            recommendations = []
            for track in top_tracks['tracks'][:limit]:
                recommendations.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track.get('preview_url'),
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'source': 'artist_top_tracks',
                    'popularity': track.get('popularity', 0)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting artist tracks: {str(e)}")
            return []
    
    def _get_album_tracks(self, sp_client, album_id: str, limit: int) -> List[Dict]:
        """Get tracks from an album."""
        try:
            # Get album tracks
            album_tracks = sp_client.album_tracks(album_id, limit=limit)
            
            recommendations = []
            for track in album_tracks['items'][:limit]:
                recommendations.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'] if 'album' in track else 'Unknown Album',
                    'preview_url': track.get('preview_url'),
                    'image_url': None,  # Would need album info for this
                    'source': 'album_tracks',
                    'popularity': track.get('popularity', 0)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting album tracks: {str(e)}")
            return []
    
    def _get_related_artists(self, sp_client, artist_id: str, limit: int) -> List[Dict]:
        """Get tracks from related artists."""
        try:
            # Skip artists that are likely to fail (based on previous experience)
            if artist_id in ['6yJCxee7QumYr820xdIsjo', '2o7k9CBUdlkyWt4qyFAdvm', '3QwPZWMfGsTvOmBJylFvrS', '5ypQRq934XJmh9eXioqKiQ']:
                logger.debug(f"Skipping artist {artist_id} - known to fail")
                return []
            
            # First, validate the artist exists
            try:
                artist_info = sp_client.artist(artist_id)
                logger.debug(f"Found artist: {artist_info['name']} (ID: {artist_id})")
            except Exception as e:
                logger.debug(f"Artist {artist_id} not found or inaccessible: {str(e)}")
                return []
            
            # Instead of related artists (deprecated), get more tracks from the same artist
            # This provides variety while using working endpoints
            try:
                top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
                
                recommendations = []
                for track in top_tracks['tracks'][:limit]:
                    recommendations.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'preview_url': track.get('preview_url'),
                        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                        'source': 'artist_variety',
                        'popularity': track.get('popularity', 0)
                    })
                
                return recommendations
                
            except Exception as e:
                logger.warning(f"Could not get top tracks for artist {artist_id}: {str(e)}")
                return []
            
        except Exception as e:
            logger.warning(f"Could not get related artists for artist {artist_id}: {str(e)}")
            return []
    
    def _remove_duplicates(self, tracks: List[Dict]) -> List[Dict]:
        """Remove duplicate tracks based on track ID."""
        seen_ids = set()
        unique_tracks = []
        
        for track in tracks:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_tracks.append(track)
        
        return unique_tracks
    
    def apply_personalization_filters(self, tracks: List[Dict], user_preferences: Dict) -> List[Dict]:
        """
        Apply personalization filters to tracks based on user preferences.
        
        This is a simplified version since we don't have audio features.
        We can filter based on artist/genre preferences and user feedback.
        """
        filtered_tracks = []
        
        for track in tracks:
            # Check if user has disliked this track before
            disliked = UserFeedback.objects.filter(
                user=self.user,
                track__spotify_id=track['id'],
                feedback_type='DISLIKE'
            ).exists()
            
            if not disliked:
                filtered_tracks.append(track)
        
        # Sort by source preference (saved tracks > top tracks > recently played)
        source_priority = {
            'saved_tracks': 3,
            'top_tracks': 2,
            'recently_played': 1,
            'artist_top_tracks': 2,
            'album_tracks': 1,
            'artist_variety': 2
        }
        
        filtered_tracks.sort(key=lambda x: source_priority.get(x.get('source', 0), 0), reverse=True)
        
        return filtered_tracks 
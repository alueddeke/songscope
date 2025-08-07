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
        self._api_cache = {}  # Cache for API results
        self._cache_ttl = 300  # 5 minutes cache TTL
    
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
    
    def get_recommendations(self, limit=20, force_fresh=False) -> List[Dict]:
        """
        Get personalized recommendations using hybrid approach.
        Combines multiple strategies based on user profile.
        
        Args:
            limit: Number of recommendations to return
            force_fresh: If True, force fresh data update regardless of timing
        """
        try:
            logger.info(f"Getting dynamic recommendations for user {self.user.id} (force_fresh: {force_fresh})")
            
            # Check cache first (unless force_fresh is True)
            if not force_fresh:
                cached_recommendations = self.profile.get_from_cache(limit)
                if cached_recommendations:
                    logger.info(f"Returning {len(cached_recommendations)} recommendations from cache")
                    return cached_recommendations
            
            # If no cache or force_fresh, generate new recommendations
            logger.info("Cache miss or force_fresh - generating new recommendations")
            
            # Clear cache when generating fresh recommendations to avoid repeats
            if force_fresh:
                logger.info("🔄 FORCE FRESH: Clearing cache and fetching fresh listening data...")
                self.profile.clear_cache()
            
            # Force fresh update if requested or if daily update is needed
            if force_fresh or self._should_update_profile() or not self._has_base_data():
                if force_fresh:
                    logger.info("🔄 FORCE FRESH: Fetching fresh listening data...")
                else:
                    logger.info("Daily profile update triggered - fetching fresh listening data...")
                self._update_profile_data()
            else:
                logger.info("Using existing profile data (updated within 24 hours)")
            
            # Get recommendations from multiple sources
            all_recommendations = []
            
            # Strategy 1: Playlist Mining (get more variety)
            if self._check_rate_limit():
                playlist_recs = self._get_playlist_recommendations(limit * 3)  # Get more to shuffle
                all_recommendations.extend(playlist_recs)
                logger.info(f"Playlist mining found {len(playlist_recs)} recommendations")
            
            # Strategy 2: Artist Network (get more variety)
            if self._check_rate_limit():
                artist_recs = self._get_artist_network_recommendations(limit * 3)  # Get more to shuffle
                all_recommendations.extend(artist_recs)
                logger.info(f"Artist network found {len(artist_recs)} recommendations")
            
            # Strategy 3: Contextual Recommendations (get more variety)
            if self._check_rate_limit():
                contextual_recs = self._get_contextual_recommendations(limit * 3)  # Get more to shuffle
                all_recommendations.extend(contextual_recs)
                logger.info(f"Contextual analysis found {len(contextual_recs)} recommendations")
            
            # If no recommendations from hybrid strategies, use fallback
            if not all_recommendations:
                logger.info("No hybrid recommendations found, using fallback...")
                return self._get_fallback_recommendations(limit)
            
            # Remove duplicates and score
            unique_recommendations = self._remove_duplicates(all_recommendations)
            scored_recommendations = self._score_recommendations(unique_recommendations)
            
            # Add more randomization for variety
            import random
            # Shuffle multiple times for better randomization
            for _ in range(3):
                random.shuffle(scored_recommendations)
            
            # Add some randomness to scores for more variety
            for rec in scored_recommendations:
                rec['score'] += random.uniform(-0.1, 0.1)  # Add small random variation
            
            # Re-sort by new scores
            scored_recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            # Filter out liked songs and recently played
            scored_recommendations = self._filter_out_liked_songs(scored_recommendations)
            scored_recommendations = self._filter_out_recently_played(scored_recommendations)
            logger.info(f"After filtering, {len(scored_recommendations)} tracks remaining")
            
            # Return top recommendations
            final_recommendations = scored_recommendations[:limit]
            
            # If we don't have enough, get more from fallback
            if len(final_recommendations) < limit:
                logger.info(f"Only have {len(final_recommendations)} recommendations, getting more from fallback...")
                fallback_recs = self._get_fallback_recommendations(limit * 2)
                
                # Filter fallback recommendations too
                fallback_recs = self._filter_out_liked_songs(fallback_recs)
                fallback_recs = self._filter_out_recently_played(fallback_recs)
                
                # Add fallback recommendations
                for rec in fallback_recs:
                    if len(final_recommendations) >= limit:
                        break
                    final_recommendations.append(rec)
                
                logger.info(f"Added {len([r for r in fallback_recs if r in final_recommendations])} from fallback")
            
            # If still not enough, duplicate some to reach the limit
            if len(final_recommendations) < limit and len(scored_recommendations) > 0:
                logger.info(f"Still only have {len(final_recommendations)} recommendations, duplicating to reach {limit}")
                while len(final_recommendations) < limit and len(scored_recommendations) > 0:
                    # Cycle through available recommendations
                    for rec in scored_recommendations:
                        if len(final_recommendations) >= limit:
                            break
                        # Create a copy with a note that it's duplicated
                        rec_copy = rec.copy()
                        rec_copy['duplicated'] = True
                        final_recommendations.append(rec_copy)
            
            logger.info(f"Generated {len(final_recommendations)} dynamic recommendations")
            
            # Debug: Log what we're returning
            for i, rec in enumerate(final_recommendations[:3]):  # Log first 3
                logger.info(f"Recommendation {i+1}: {rec['name']} by {rec['artist']} (source: {rec['source']}, popularity: {rec.get('popularity', 'N/A')})")
            
            # Add to cache
            self.profile.add_to_cache(final_recommendations)
            logger.info(f"Added {len(final_recommendations)} recommendations to cache (cache size: {self.profile.cache_size()})")
            
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
    
    def _should_update_profile(self) -> bool:
        """Check if profile needs daily update"""
        from django.utils import timezone
        from datetime import timedelta
        
        last_update = self.profile.updated_at
        days_since_update = (timezone.now() - last_update).days
        return days_since_update >= 1
    
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
            self._update_saved_tracks(sp)  # Need this for fallback filtering
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
            
            # Get ALL saved tracks (Spotify liked songs) - increase limit significantly
            saved_tracks = sp.current_user_saved_tracks(limit=1000)
            saved_tracks_list = [
                {
                    'id': item['track']['id'],
                    'name': item['track']['name'],
                    'artist': item['track']['artists'][0]['name'],
                    'artist_id': item['track']['artists'][0]['id'],
                    'added_at': item['added_at']
                }
                for item in saved_tracks['items']
            ]
            
            self.profile.data['base_data']['saved_tracks'] = saved_tracks_list
            
            # Log how many liked songs we actually loaded
            logger.info(f"Loaded {len(saved_tracks_list)} Spotify liked songs")
            logger.info(f"Sample liked songs: {[track['name'] for track in saved_tracks_list[:5]]}")
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
            
            # Get more recent tracks for better patterns
            recent_tracks = sp.current_user_recently_played(limit=100)
            
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
            
            # Shuffle playlists to get different ones each time
            import random
            random.shuffle(playlists)
            
            for playlist in playlists[:10]:  # Get more playlists for variety
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
                                'score': 0.0,  # Will be calculated later
                                'popularity': track.get('popularity', 0)
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
            
            # Shuffle artists to get different ones each time
            import random
            random.shuffle(all_artists)
            
            for artist in all_artists[:6]:  # Get more artists for variety
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
                                    'score': 0.0,
                                    'popularity': track.get('popularity', 0)
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
        """Get contextual recommendations based on time using working endpoints"""
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
            
            logger.info(f"Getting contextual recommendations for {time_period} period (hour: {current_hour})")
            
            # Get tracks from current time period
            track_ids = patterns.get(time_period, [])
            
            if track_ids and self._check_rate_limit():
                try:
                    sp = self._get_spotify_client()
                    if sp:
                        # Get track details for recent tracks from this time period
                        recent_tracks = track_ids[:10]  # Get up to 10 tracks
                        
                        logger.info(f"Getting details for {len(recent_tracks)} recent tracks from {time_period}")
                        
                        # Get track details using working endpoint
                        tracks_response = sp.tracks(recent_tracks)
                        
                        # Get similar tracks by finding artists from recent tracks
                        artist_ids = set()
                        for track in tracks_response['tracks']:
                            if track and track['artists']:
                                artist_ids.add(track['artists'][0]['id'])
                        
                        # Get top tracks from these artists (contextual recommendations)
                        for artist_id in list(artist_ids)[:3]:  # Use up to 3 artists
                            try:
                                if self._check_rate_limit():
                                    artist_top_tracks = sp.artist_top_tracks(artist_id, country='US')
                                    
                                    for track in artist_top_tracks['tracks']:
                                        if track['id'] not in track_ids:  # Don't include the original tracks
                                            recommendations.append({
                                                'id': track['id'],
                                                'name': track['name'],
                                                'artist': track['artists'][0]['name'],
                                                'album': track['album']['name'],
                                                'preview_url': track.get('preview_url'),
                                                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                                'source': 'contextual',
                                                'time_period': time_period,
                                                'score': 0.3,  # Boost contextual recommendations
                                                'popularity': track.get('popularity', 0)
                                            })
                                            
                                            if len(recommendations) >= limit:
                                                break
                            except Exception as e:
                                logger.debug(f"Error getting top tracks for artist {artist_id}: {str(e)}")
                                continue
                            
                            if len(recommendations) >= limit:
                                break
                                
                except Exception as e:
                    logger.warning(f"Error getting contextual track details: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in contextual recommendations: {str(e)}")
        
        logger.info(f"Generated {len(recommendations)} contextual recommendations for {time_period}")
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
    
    # Removed complex hidden gems filter - replaced with simple _filter_out_liked_songs
    
    def _filter_out_liked_songs(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Efficient filter to exclude songs the user has liked/saved.
        Uses Spotify's check_users_saved_tracks endpoint to check each song individually.
        """
        filtered_recommendations = []
        
        # Get user's top artists (they know these well)
        top_artist_names = {
            artist['name'] for artist in self.profile.data.get('base_data', {}).get('top_artists', [])
        }
        
        logger.info(f"Filtering {len(recommendations)} recommendations against {len(top_artist_names)} top artists")
        logger.info(f"Sample top artists: {list(top_artist_names)[:5] if top_artist_names else 'None'}")
        
        # Get Spotify client
        sp = self._get_spotify_client()
        if not sp:
            logger.error("No Spotify client available for filtering")
            return recommendations
        
        # Check which tracks the user has saved (liked)
        track_ids_to_check = [rec['id'] for rec in recommendations]
        
        try:
            if not self._check_rate_limit():
                logger.warning("Rate limit approaching, skipping liked songs check")
                return recommendations
            
            # Spotify API has a limit on how many IDs you can check at once
            # Process in batches of 20 (Spotify's limit is usually 50, but we'll be safe)
            batch_size = 20
            all_saved_status = []
            
            for i in range(0, len(track_ids_to_check), batch_size):
                batch_ids = track_ids_to_check[i:i + batch_size]
                logger.info(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} tracks")
                
                try:
                    batch_saved_status = sp.current_user_saved_tracks_contains(batch_ids)
                    all_saved_status.extend(batch_saved_status)
                    logger.info(f"Batch {i//batch_size + 1} results: {batch_saved_status}")
                except Exception as e:
                    logger.error(f"Error checking batch {i//batch_size + 1}: {str(e)}")
                    # If batch fails, assume none are saved for this batch
                    all_saved_status.extend([False] * len(batch_ids))
            
            saved_status = all_saved_status
            logger.info(f"Checked {len(track_ids_to_check)} tracks against user's liked songs")
            logger.info(f"Saved status sample: {saved_status[:5] if saved_status else 'None'}")
            
        except Exception as e:
            logger.error(f"Error checking saved tracks: {str(e)}")
            # Fallback: use cached saved tracks from profile
            logger.info("Using fallback: checking against cached saved tracks")
            cached_saved_track_ids = {
                track['id'] for track in self.profile.data.get('base_data', {}).get('saved_tracks', [])
            }
            
            filtered_recommendations = []
            filtered_out_count = 0
            
            for rec in recommendations:
                should_filter = False
                filter_reason = ""
                
                # Check if user has liked this track on Spotify (cached)
                if rec['id'] in cached_saved_track_ids:
                    should_filter = True
                    filter_reason = f"Spotify liked song (cached): {rec['name']} by {rec['artist']}"
                    logger.info(f"🚫 FILTERED OUT LIKED SONG (CACHED): {rec['id']} - {rec['name']} by {rec['artist']}")
                
                # Skip if from user's top artists (they know these artists well)
                elif rec['artist'] in top_artist_names:
                    should_filter = True
                    filter_reason = f"Top artist: {rec['name']} by {rec['artist']}"
                    logger.info(f"🚫 FILTERED OUT TOP ARTIST: {rec['name']} by {rec['artist']}")
                
                if should_filter:
                    filtered_out_count += 1
                    continue
                
                # Keep the track
                logger.info(f"✅ KEEPING TRACK: {rec['name']} by {rec['artist']} (not liked, not top artist)")
                filtered_recommendations.append(rec)
            
            logger.info(f"Fallback filtered {len(recommendations)} -> {len(filtered_recommendations)} tracks (filtered out {filtered_out_count})")
            return filtered_recommendations
        
        filtered_out_count = 0
        
        for i, rec in enumerate(recommendations):
            should_filter = False
            filter_reason = ""
            
            # Check if user has liked this track on Spotify
            if i < len(saved_status) and saved_status[i]:
                should_filter = True
                filter_reason = f"Spotify liked song: {rec['name']} by {rec['artist']}"
                logger.info(f"🚫 FILTERED OUT LIKED SONG: {rec['id']} - {rec['name']} by {rec['artist']}")
            
            # Skip if from user's top artists (they know these artists well)
            elif rec['artist'] in top_artist_names:
                should_filter = True
                filter_reason = f"Top artist: {rec['name']} by {rec['artist']}"
                logger.info(f"🚫 FILTERED OUT TOP ARTIST: {rec['name']} by {rec['artist']}")
            
            if should_filter:
                filtered_out_count += 1
                continue
            
            # Keep the track
            logger.info(f"✅ KEEPING TRACK: {rec['name']} by {rec['artist']} (not liked, not top artist)")
            filtered_recommendations.append(rec)
        
        logger.info(f"Filtered {len(recommendations)} -> {len(filtered_recommendations)} tracks (filtered out {filtered_out_count})")
        return filtered_recommendations
    
    def _filter_out_recently_played(self, recommendations: List[Dict]) -> List[Dict]:
        """Filter out tracks the user has played recently"""
        try:
            sp = self._get_spotify_client()
            if not sp:
                return recommendations
            
            # Get recently played track IDs
            recent_tracks = sp.current_user_recently_played(limit=50)
            recent_track_ids = {item['track']['id'] for item in recent_tracks['items']}
            
            filtered_recommendations = []
            filtered_count = 0
            
            for rec in recommendations:
                if rec['id'] in recent_track_ids:
                    logger.info(f"Filtered out recently played: {rec['name']} by {rec['artist']}")
                    filtered_count += 1
                    continue
                filtered_recommendations.append(rec)
            
            logger.info(f"Filtered out {filtered_count} recently played tracks")
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Error filtering recently played: {str(e)}")
            return recommendations
    
    def add_feedback(self, track_id: str, feedback_type: str, track_info: Dict = None):
        """Add user feedback and update profile"""
        self.profile.add_feedback(track_id, feedback_type, track_info)
        logger.info(f"Added feedback: {feedback_type} for track {track_id}")
    
    def remove_feedback(self, track_id: str):
        """Remove user feedback from profile"""
        try:
            # Remove from feedback history
            feedback_history = self.profile.data.get('preferences', {}).get('feedback_history', [])
            updated_history = [fb for fb in feedback_history if fb.get('track_id') != track_id]
            
            if 'preferences' not in self.profile.data:
                self.profile.data['preferences'] = {}
            self.profile.data['preferences']['feedback_history'] = updated_history
            
            # Update liked artists if this was a like feedback
            liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
            if track_info := next((fb for fb in feedback_history if fb.get('track_id') == track_id), None):
                artist_name = track_info.get('artist')
                if artist_name in liked_artists:
                    liked_artists.remove(artist_name)
                    self.profile.data['preferences']['liked_artists'] = liked_artists
            
            self.profile.save()
            logger.info(f"Removed feedback for track {track_id}")
            
        except Exception as e:
            logger.error(f"Error removing feedback: {str(e)}")
    
    def add_ai_feedback(self, interpretation: Dict, track_info: Dict = None):
        """Add AI-interpreted feedback to user profile"""
        try:
            if 'preferences' not in self.profile.data:
                self.profile.data['preferences'] = {}
            
            # Store AI feedback in profile
            ai_feedback_history = self.profile.data['preferences'].get('ai_feedback_history', [])
            ai_feedback_entry = {
                'timestamp': timezone.now().isoformat(),
                'interpretation': interpretation,
                'track_info': track_info,
                'confidence': interpretation.get('confidence', 0.0)
            }
            ai_feedback_history.append(ai_feedback_entry)
            
            # Keep only last 50 AI feedback entries
            if len(ai_feedback_history) > 50:
                ai_feedback_history = ai_feedback_history[-50:]
            
            self.profile.data['preferences']['ai_feedback_history'] = ai_feedback_history
            
            # Update recommendation weights based on AI feedback
            self._update_weights_from_ai_feedback(interpretation)
            
            self.profile.save()
            logger.info(f"Added AI feedback to profile: {interpretation}")
            
        except Exception as e:
            logger.error(f"Error adding AI feedback: {str(e)}")
    
    def _update_weights_from_ai_feedback(self, interpretation: Dict):
        """Update recommendation weights based on AI feedback"""
        try:
            weights = self.profile.get_recommendation_weights()
            
            # Apply AI feedback to weights
            if interpretation.get('tempo_preference') == 'faster':
                weights['tempo_weight'] = min(weights.get('tempo_weight', 1.0) + 0.1, 2.0)
            elif interpretation.get('tempo_preference') == 'slower':
                weights['tempo_weight'] = max(weights.get('tempo_weight', 1.0) - 0.1, 0.1)
            
            if interpretation.get('energy_preference') == 'higher':
                weights['energy_weight'] = min(weights.get('energy_weight', 1.0) + 0.1, 2.0)
            elif interpretation.get('energy_preference') == 'lower':
                weights['energy_weight'] = max(weights.get('energy_weight', 1.0) - 0.1, 0.1)
            
            if interpretation.get('mood_preference') == 'happier':
                weights['valence_weight'] = min(weights.get('valence_weight', 1.0) + 0.1, 2.0)
            elif interpretation.get('mood_preference') == 'sadder':
                weights['valence_weight'] = max(weights.get('valence_weight', 1.0) - 0.1, 0.1)
            
            # Store specific artists/genres to avoid/prefer
            if interpretation.get('specific_artists'):
                if 'avoid_artists' not in weights:
                    weights['avoid_artists'] = []
                weights['avoid_artists'].extend(interpretation['specific_artists'])
            
            if interpretation.get('specific_genres'):
                if 'prefer_genres' not in weights:
                    weights['prefer_genres'] = []
                weights['prefer_genres'].extend(interpretation['specific_genres'])
            
            self.profile.update_weights(weights)
            logger.info(f"Updated weights from AI feedback: {weights}")
            
        except Exception as e:
            logger.error(f"Error updating weights from AI feedback: {str(e)}")
    
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
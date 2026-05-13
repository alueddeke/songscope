"""
Hybrid Recommendation Engine - Combines multiple strategies for better recommendations

This engine implements a sophisticated recommendation system that:
1. Uses playlist mining to find hidden gems
2. Leverages artist networks for discovery
3. Applies contextual analysis for time/mood-based recommendations
4. Learns from user feedback to improve over time
5. Respects Spotify API rate limits and terms of service
"""

import math
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from datetime import datetime, timedelta
import json
import random
from collections import defaultdict
import spotipy
from spotipy.exceptions import SpotifyException
from django.conf import settings
from apps.core.models import UserProfile, Track, UserFeedback
from apps.core.models import SpotifyToken
from apps.spotify.utils import rate_limit_monitor, get_spotipy_client
from .track_discovery_engine import TrackDiscoveryEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thompson Sampling constants (Phase 3)
# ---------------------------------------------------------------------------
# Static default weights for cold-start sources (sum = 1.0)
SOURCE_DEFAULTS = {
    'playlist_mining': 0.3,
    'artist_network': 0.25,
    'genre_search': 0.2,
    'related_artists': 0.15,
    'contextual': 0.1,
}

# Minimum number of observations (successes + failures) before a source
# transitions from cold-start (static default) to Beta sampling.
COLD_START_THRESHOLD = 3


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
    
    def get_recommendation_weights(self) -> dict:
        """
        Thompson Sampling bandit for source weight selection.

        For each of the 5 candidate sources, draw a weight from Beta(s+1, f+1)
        where s = successes (liked tracks from this source) and f = failures
        (disliked/skipped tracks from this source), stored in
        UserProfile.data['source_stats'].

        Cold-start rule: if a source has fewer than COLD_START_THRESHOLD total
        observations (s+f < 3), use the static SOURCE_DEFAULTS weight for that
        source instead of sampling.

        If source_stats is completely empty, return static defaults unchanged.

        Returns a dict with all 5 source keys (normalized to sum to 1.0) plus
        a 'bandit_active' sentinel key set to True to signal Phase 3 is wired.
        """
        source_stats = self.profile.data.get('source_stats', {})

        # Pure cold-start: no stats at all — return neutral 1.0 weights + sentinel.
        # Using 1.0 (not the static defaults) keeps the source multiplier neutral
        # when no source_stats have been recorded yet, so the base score formula
        # is unaffected during cold-start.
        if not source_stats:
            result = {source: 1.0 for source in SOURCE_DEFAULTS}
            result['bandit_active'] = True
            return result

        # Sample or use default for each source
        thetas = {}
        for source, default_weight in SOURCE_DEFAULTS.items():
            stats = source_stats.get(source, {'s': 0, 'f': 0})
            n = stats.get('s', 0) + stats.get('f', 0)
            if n < COLD_START_THRESHOLD:
                # Cold-start for this source: use static default
                thetas[source] = default_weight
            else:
                # Enough observations: sample from Beta(s+1, f+1)
                thetas[source] = random.betavariate(
                    stats.get('s', 0) + 1,
                    stats.get('f', 0) + 1,
                )

        # Normalize to max=1.0 so the best source gets a 1.0 multiplier.
        # Normalizing to sum=1.0 would make each weight ~0.2, penalizing warm
        # sources relative to the cold-start 1.0 baseline — the bandit would
        # work backwards.
        max_weight = max(thetas.values()) or 1.0
        result = {k: v / max_weight for k, v in thetas.items()}
        result['bandit_active'] = True
        return result

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

            # Strategy 5: Related Artist Deep Cuts (Bug 7 fix — was missing)
            if self._check_rate_limit():
                related_recs = self._get_related_artist_recommendations(limit * 2)
                all_recommendations.extend(related_recs)
                logger.info(
                    f"Related artist strategy found {len(related_recs)} recommendations"
                )

            # If no recommendations from hybrid strategies, use fallback
            if not all_recommendations:
                logger.info("No hybrid recommendations found, using fallback...")
                return self._get_fallback_recommendations(limit)
            
            # Remove duplicates and score
            unique_recommendations = self._remove_duplicates(all_recommendations)
            scored_recommendations = self._score_recommendations(unique_recommendations)
            
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
                logger.debug(f"Recommendation {i+1}: {rec['name']} by {rec['artist']} (source: {rec['source']}, popularity: {rec.get('popularity', 'N/A')})")
            
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
            spotify_token = SpotifyToken.objects.filter(user=self.user).first()
            if not spotify_token or spotify_token.is_expired():
                logger.error("No valid Spotify token available for profile update")
                return
            
            sp = get_spotipy_client(spotify_token.access_token)

            # Ensure required keys exist for both new and legacy profiles
            self.profile.data.setdefault('base_data', {})
            self.profile.data.setdefault('preferences', {
                'liked_artists': [], 'disliked_artists': [], 'feedback_history': []
            })

            # Update base data with error handling
            self._update_top_artists(sp)
            self._update_saved_tracks(sp)  # Need this for fallback filtering
            self._update_playlists(sp)
            self._update_listening_patterns(sp)
            self._build_taste_vector()

            # Mark as updated
            self.profile.save()
            logger.info(f"Updated profile for user {self.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            self.profile.data.setdefault('errors', []).append({
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
            
            # Cap at 10 pages (500 tracks) — unbounded pagination causes memory spikes
            # and exhausts Spotify API budget for users with large libraries.
            MAX_SAVED_PAGES = 10
            results = sp.current_user_saved_tracks(limit=50)
            all_items = list(results['items'])
            page_count = 1
            while results['next'] and page_count < MAX_SAVED_PAGES:
                results = sp.next(results)
                all_items.extend(results['items'])
                page_count += 1
            saved_tracks_list = [
                {
                    'id': item['track']['id'],
                    'name': item['track']['name'],
                    'artist': item['track']['artists'][0]['name'],
                    'artist_id': item['track']['artists'][0]['id'],
                    'added_at': item['added_at']
                }
                for item in all_items
            ]
            
            self.profile.data['base_data']['saved_tracks'] = saved_tracks_list
            
            # Log how many liked songs we actually loaded
            logger.info(f"Loaded {len(saved_tracks_list)} Spotify liked songs")
            logger.debug(f"Sample liked songs: {[track['name'] for track in saved_tracks_list[:5]]}")
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
            
            # Get more recent tracks for better patterns (Spotify max is 50)
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
        self.profile.data.setdefault('errors', []).append({
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
                        track = item.get('track')
                        if not track or not track.get('id'):  # guard against null/local tracks
                            continue
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

    def _get_related_artist_recommendations(self, limit: int) -> List[Dict]:
        """
        Strategy 5: Related Artist Deep Cuts.

        For each of the user's top artists, query Spotify's
        `artist_related_artists` graph and pull low-popularity album cuts
        from those related artists. This is the most natural deep-cut
        source — it expands beyond the user's known artists into
        adjacent-but-unfamiliar territory.

        Notes:
        - The track_discovery_engine has a workaround that uses
          `artist_top_tracks` instead of `artist_related_artists`. The
          ROADMAP explicitly calls for adding the live endpoint here, so
          we use it directly. If the endpoint is soft-deprecated and
          returns an empty list, we log it (Pitfall 5 in RESEARCH) and
          return whatever candidates we collected.
        - Popularity threshold < 40 mirrors the existing strategies'
          deep-cut definition (see _get_artist_network_recommendations).
        """
        recommendations: List[Dict] = []
        top_artists = self.profile.data.get('base_data', {}).get('top_artists', [])
        if not top_artists:
            logger.info("Strategy 5 (related artists): no top artists available, skipping")
            return []

        sp = self._get_spotify_client()
        if not sp:
            logger.info("Strategy 5 (related artists): no spotify client, skipping")
            return []

        for artist in top_artists[:4]:  # cap seed artists to keep API budget bounded
            if not self._check_rate_limit() or len(recommendations) >= limit:
                break
            artist_id = artist.get('id')
            if not artist_id:
                continue
            try:
                related = sp.artist_related_artists(artist_id)
                related_artists = related.get('artists', []) if related else []
                logger.info(
                    f"artist_related_artists: {len(related_artists)} related to "
                    f"{artist.get('name', 'unknown')}"
                )
                for rel_artist in related_artists[:5]:
                    if len(recommendations) >= limit or not self._check_rate_limit():
                        break
                    try:
                        albums = sp.artist_albums(
                            rel_artist['id'],
                            album_type='album',
                            limit=2,
                            country='US',
                        )
                        for album in albums.get('items', []):
                            if len(recommendations) >= limit:
                                break
                            album_tracks = sp.album_tracks(album['id'], limit=8)
                            track_ids = [
                                t['id'] for t in album_tracks.get('items', [])
                                if t.get('id')
                            ]
                            if not track_ids:
                                continue
                            full_tracks = sp.tracks(track_ids)
                            for track in full_tracks.get('tracks', []):
                                if not track:
                                    continue
                                if track.get('popularity', 100) >= 40:
                                    continue
                                recommendations.append({
                                    'id': track['id'],
                                    'name': track['name'],
                                    'artist': track['artists'][0]['name']
                                    if track.get('artists') else rel_artist.get('name', ''),
                                    'album': album.get('name', ''),
                                    'preview_url': track.get('preview_url'),
                                    'image_url': (
                                        album['images'][0]['url']
                                        if album.get('images') else None
                                    ),
                                    'source': 'related_artists',
                                    'score': 0.0,
                                    'popularity': track.get('popularity', 0),
                                })
                                if len(recommendations) >= limit:
                                    break
                    except Exception as inner_e:
                        logger.warning(
                            f"related_artists inner loop failed for "
                            f"{rel_artist.get('name', 'unknown')}: {inner_e}"
                        )
                        continue
            except Exception as e:
                logger.warning(
                    f"artist_related_artists failed for "
                    f"{artist.get('name', 'unknown')}: {e}"
                )
                continue
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
                                                'score': 0.0,
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
            spotify_token = SpotifyToken.objects.filter(user=self.user).first()
            if not spotify_token or spotify_token.is_expired():
                return None

            return get_spotipy_client(spotify_token.access_token)
        except Exception as e:
            logger.error(f"Error getting Spotify client: {str(e)}")
            return None

    def _get_persistent_exclusion_set(self) -> set:
        """
        Return a set of Spotify track IDs the user has already encountered.

        DB-backed (no Spotify API calls), assembled from:
          - RecommendationLog: every track ever recommended (excluding the
            'error_log' sentinel created by RecommendationLog.log_error()).
          - DailyGem: every track ever shown as the user's daily gem.

        Returns a materialized Python `set` so membership checks in the
        candidate filter loop are O(1) — wrapping the QuerySet in set()
        avoids the N+1 SQL pattern that would arise from `track_id in qs`.
        """
        # Local import keeps the module's top-level imports lean and avoids
        # any circular-import risk between recommendations and core apps.
        from apps.core.models import RecommendationLog, DailyGem

        logged_ids = set(
            RecommendationLog.objects
            .filter(user=self.user)
            .exclude(track__spotify_id='error_log')
            .values_list('track__spotify_id', flat=True)
        )
        gemmed_ids = set(
            DailyGem.objects
            .filter(user=self.user)
            .values_list('track__spotify_id', flat=True)
        )
        return logged_ids | gemmed_ids

    def _remove_duplicates(self, recommendations: List[Dict]) -> List[Dict]:
        """Remove duplicate tracks based on track ID"""
        seen_ids = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _build_taste_vector(self):
        """Build genre frequency vector from top_artists and merge with feedback-learned increments.

        Overwiting the whole vector on each 24h refresh would wipe feedback-learned genre
        weights accumulated via apply_feedback_learning. Instead we compute the base counts
        from top_artists and take the max of the base value and any feedback-learned value,
        preserving pure-feedback genres not in top_artists entirely.
        """
        top_artists = self.profile.data.get('base_data', {}).get('top_artists', [])
        base_vector = {}
        for artist in top_artists:
            for genre in artist.get('genres', []):
                base_vector[genre] = base_vector.get(genre, 0) + 1

        existing = self.profile.data.get('taste_vector', {})
        merged = dict(base_vector)
        for genre, val in existing.items():
            if genre in merged:
                merged[genre] = max(merged[genre], val)
            else:
                merged[genre] = val

        self.profile.data['taste_vector'] = merged
        logger.info(f"Built taste vector with {len(merged)} genres from {len(top_artists)} artists")

    def _cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
        """Cosine similarity between two genre count dicts. Returns 0.0 if either empty."""
        if not vec_a or not vec_b:
            return 0.0
        keys = set(vec_a.keys()) | set(vec_b.keys())
        a = np.array([vec_a.get(k, 0.0) for k in keys])
        b = np.array([vec_b.get(k, 0.0) for k in keys])
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _score_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Score candidates: 0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier (LOCKED formula)"""
        taste_vector = self.profile.data.get('taste_vector', {})
        liked_artists = self.profile.data.get('preferences', {}).get('liked_artists', [])
        disliked_artists = self.profile.data.get('preferences', {}).get('disliked_artists', [])

        # Build artist->genres lookup from already-fetched top_artists (zero extra API calls)
        artist_genre_lookup = {
            a['name']: a.get('genres', [])
            for a in self.profile.data.get('base_data', {}).get('top_artists', [])
        }

        # Thompson Sampling source weights — computed once before the scoring loop
        source_weights = self.get_recommendation_weights()

        # Bell-curve novelty: read preferred_popularity_range once before the loop.
        # Defaults: midpoint=30, width=20 (cold-start / no preference set).
        prefs = self.profile.data.get('preferences', {})
        pop_range = prefs.get('preferred_popularity_range', {'midpoint': 30, 'width': 20})
        midpoint = pop_range.get('midpoint', 30)
        width = pop_range.get('width', 20) or 20  # guard against width=0 → ZeroDivisionError

        for rec in recommendations:
            artist_name = rec.get('artist', '')

            # genre_sim: cosine similarity between candidate genres and user taste vector
            candidate_genres = {g: 1.0 for g in artist_genre_lookup.get(artist_name, [])}
            genre_sim = self._cosine_similarity(candidate_genres, taste_vector)

            # novelty: Gaussian bell-curve centred at preferred popularity midpoint.
            # novelty = exp(-((popularity - midpoint)^2) / (2 * width^2))
            # Peaks at 1.0 when popularity == midpoint; decays symmetrically outward.
            popularity = rec.get('popularity', 50)
            novelty = math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))

            # feedback_multiplier: artist-level preference signal
            if artist_name in liked_artists:
                feedback_multiplier = 1.5
            elif artist_name in disliked_artists:
                feedback_multiplier = 0.5
            else:
                feedback_multiplier = 1.0

            # Store score components for downstream use (e.g., get_daily_gem API response)
            rec['score_breakdown'] = {
                'genre_sim': round(genre_sim, 4),
                'novelty': round(novelty, 4),
                'feedback_multiplier': round(feedback_multiplier, 4),
                'source': rec.get('source', ''),
            }

            # LOCKED formula — do not adjust weights
            rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier

            # Post-score multiplier: apply Thompson-sampled source weight.
            # Unknown source (no key) gets 1.0 — neutral, no boost or penalty.
            rec['score'] *= source_weights.get(rec.get('source', ''), 1.0)

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
    
    def _filter_out_liked_songs(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Exclude tracks the user has already encountered, using the DB-backed
        persistent exclusion set. No live Spotify API calls — eliminates rate
        limit burn and the fallback-to-stale-cache path.

        Bug 5 fix: removed the artist-name filter — that was filtering out
        deep cuts by familiar artists, which is the OPPOSITE of what a
        discovery engine wants. Track-level exclusion via the persistent set
        is the correct precision.

        Bug 6 fix: replaced batched saved-tracks API calls with a single
        in-memory set lookup. The real-time saved-tracks check is preserved
        as a last-gate inside `get_daily_gem` in views.py (line ~1050) —
        that is the right place for it.
        """
        exclusion_ids = self._get_persistent_exclusion_set()
        logger.info(
            f"DB exclusion set has {len(exclusion_ids)} track IDs "
            f"(combined RecommendationLog + DailyGem history)"
        )

        filtered = []
        filtered_out = 0
        for rec in recommendations:
            rec_id = rec.get('id')
            if rec_id and rec_id in exclusion_ids:
                filtered_out += 1
                logger.debug(
                    f"FILTERED (DB exclusion): {rec.get('name')} by "
                    f"{rec.get('artist')} [{rec_id}]"
                )
                continue
            filtered.append(rec)

        logger.info(
            f"_filter_out_liked_songs: {len(recommendations)} candidates -> "
            f"{len(filtered)} after exclusion (removed {filtered_out})"
        )
        return filtered
    
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
                    logger.debug(f"Filtered out recently played: {rec['name']} by {rec['artist']}")
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
            if entry := next((fb for fb in feedback_history if fb.get('track_id') == track_id), None):
                # artist is nested under 'track_info', not at the top level
                artist_name = entry.get('track_info', {}).get('artist')
                if artist_name and artist_name in liked_artists:
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
            
            self.profile.save()
            logger.info(f"Added AI feedback to profile: {interpretation}")
            
        except Exception as e:
            logger.error(f"Error adding AI feedback: {str(e)}")
    
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
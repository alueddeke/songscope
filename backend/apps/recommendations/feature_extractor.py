import numpy as np
from collections import defaultdict
import logging
from typing import Dict, List, Optional
import spotipy

logger = logging.getLogger(__name__)

# Base weights from data scientist (kept as fallback)
BASE_WEIGHTS = {
    'acousticness': 0.103040,
    'instrumentalness': 0.0898047,
    'energy': 0.0886158,
    'valence': 0.0863662,
    'danceability': 0.08025012,
    'tempo': 0.0738526,
    'loudness': 0.06975411,
    'duration_ms': 0.0694154,
    'liveness': 0.0637700,
    'key': 0.0592409,
    'mode': 0.0541063
}

def extract_current_user_profile(top_tracks, recent_tracks, sp):
    """
    Extract a user's music profile from their current listening data.
    
    Args:
        top_tracks (list): User's top tracks from Spotify
        recent_tracks (list): User's recently played tracks
        sp: Spotify client instance
    
    Returns:
        dict: User profile containing weighted features and preferences
    """
    try:
        # Combine tracks for analysis
        all_tracks = top_tracks + recent_tracks
        
        # Extract audio features
        features = extract_audio_features(all_tracks, sp)
        if not features:
            return None
            
        # Calculate adaptive weights
        weights = calculate_adaptive_weights(features)
        
        # Calculate weighted averages for each feature
        weighted_features = {}
        for feature, values in features.items():
            if values:
                weighted_features[feature] = np.average(values, weights=[weights[feature]] * len(values))
        
        # Extract top genres and artists
        top_genres = []
        top_artists = []
        for track in all_tracks:
            if 'artists' in track:
                artist = track['artists'][0]
                if 'genres' in artist and artist['genres']:
                    top_genres.extend(artist['genres'])
                if 'name' in artist:
                    top_artists.append(artist['name'])
        
        # Get unique genres and artists, sorted by frequency
        top_genres = [list(x) for x in enumerate(sorted(set(top_genres), 
                     key=lambda x: top_genres.count(x), reverse=True))][:10]
        top_artists = [list(x) for x in enumerate(sorted(set(top_artists), 
                      key=lambda x: top_artists.count(x), reverse=True))][:10]
        
        return {
            'weighted_features': weighted_features,
            'top_genres': top_genres,
            'top_artists': top_artists
        }
        
    except Exception as e:
        logger.error(f"Error extracting user profile: {str(e)}")
        return None

def calculate_feature_variance(tracks_features: Dict[str, List[float]]) -> Dict[str, float]:
    """
    Calculate variance in user's listening patterns for each feature.
    """
    variances = {}
    for feature in BASE_WEIGHTS.keys():
        if feature in tracks_features and tracks_features[feature]:
            variances[feature] = np.var(tracks_features[feature])
    return variances

def calculate_adaptive_weights(current_tracks_features: Dict[str, List[float]]) -> Dict[str, float]:
    """Calculate personalized feature weights based on current listening patterns."""
    try:
        variances = calculate_feature_variance(current_tracks_features)
        
        if not variances:
            return BASE_WEIGHTS
            
        inverse_variances = {
            feature: 1 / (variance + 1e-6)
            for feature, variance in variances.items()
        }
        
        total_weight = sum(inverse_variances.values())
        adaptive_weights = {
            feature: weight / total_weight 
            for feature, weight in inverse_variances.items()
        }
        
        final_weights = {}
        for feature in BASE_WEIGHTS.keys():
            adaptive_weight = adaptive_weights.get(feature, BASE_WEIGHTS[feature])
            final_weights[feature] = (0.7 * adaptive_weight) + (0.3 * BASE_WEIGHTS[feature])
            
        return final_weights
        
    except Exception as e:
        logger.error(f"Error calculating adaptive weights: {str(e)}")
        return BASE_WEIGHTS

def extract_audio_features(tracks, sp) -> Optional[Dict[str, List[float]]]:
    """Extract audio features from tracks using Spotify API."""
    try:
        track_ids = [track['id'] for track in tracks]
        audio_features = sp.audio_features(track_ids)
        
        if not audio_features:
            logger.error("No audio features returned from Spotify API")
            return None
        
        features = defaultdict(list)
        for track_features in audio_features:
            if track_features:
                for feature in BASE_WEIGHTS.keys():
                    if feature in track_features:
                        features[feature].append(track_features[feature])
        
        return features
    except Exception as e:
        logger.error(f"Error extracting audio features: {str(e)}")
        return None
def get_recommendations(user_preferences: Dict, top_tracks: List[Dict], sp) -> Optional[List[Dict]]:
    """Get personalized recommendations using adaptive weights."""
    try:
        # Extract features from current top tracks
        current_features = extract_audio_features(top_tracks, sp)
        if not current_features:
            logger.warning("Using base weights due to feature extraction failure")
            weights = BASE_WEIGHTS
        else:
            weights = calculate_adaptive_weights(current_features)
        
        # Get seed tracks (using first few top tracks)
        seed_tracks = [track['id'] for track in top_tracks[:5]]
        
        # Calculate target values for recommendations
        targets = {}
        if current_features:
            for feature, values in current_features.items():
                if values:
                    weighted_avg = np.average(values, weights=[weights[feature]] * len(values))
                    targets[f'target_{feature}'] = weighted_avg
        
        # Get recommendations from Spotify
        recommendations = sp.recommendations(
            seed_tracks=seed_tracks,
            limit=20,
            **targets
        )
        
        if not recommendations or 'tracks' not in recommendations:
            logger.error("No recommendations returned from Spotify API")
            return None
            
        return recommendations['tracks']
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}", exc_info=True)
        return None
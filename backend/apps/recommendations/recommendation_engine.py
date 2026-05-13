from django.db.models import Avg, F, Value, FloatField
from datetime import timedelta
from django.utils import timezone
import numpy as np
import logging
from typing import List, Dict, Any
from apps.core.models import UserPreferences, UserFeedback, Track
from .personalization_engine import PersonalizationEngine
from .track_discovery_engine import TrackDiscoveryEngine

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, user):
        self.user = user
        self.preferences = UserPreferences.objects.get_or_create(user=user)[0]
        
    def get_personalized_recommendations(self, sp_client, limit=20):
        """Get recommendations using the track discovery engine (no Spotify recommendations API)"""
        try:
            logger.info(f"Starting track discovery recommendations for user {self.user.id}")
            
            # Use the track discovery engine instead of Spotify's recommendations API
            discovery_engine = TrackDiscoveryEngine(self.user)
            recommendations = discovery_engine.get_personalized_recommendations(sp_client, limit)
            
            logger.info(f"Generated {len(recommendations)} recommendations from track discovery")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in get_personalized_recommendations: {str(e)}")
            return []
    
    def _calculate_targets(self, feedback_queryset) -> Dict[str, float]:
        """Calculate average features from feedback"""
        try:
            features = self.preferences.feature_weights.keys()
            targets = {}
            
            for feature in features:
                # Extract the feature value from the JSON field and calculate average
                avg_value = feedback_queryset.annotate(
                    feature_value=FloatField(F(f'track_features__{feature}'))
                ).aggregate(avg=Avg('feature_value'))['avg']
                
                if avg_value is not None:
                    targets[feature] = float(avg_value)
            
            return targets
            
        except Exception as e:
            logger.error(f"Error calculating targets: {str(e)}")
            # Fall back to default features
            return {
                'acousticness': 0.5,
                'danceability': 0.5,
                'energy': 0.5,
                'instrumentalness': 0.5,
                'valence': 0.5,
                'tempo': 120.0
            }
    
    def _calculate_targets_from_features(self, features: List[Dict]) -> Dict[str, float]:
        """Calculate average features from Spotify audio features response"""
        valid_features = [f for f in features if f is not None]
        if not valid_features:
            return self._get_default_targets()
            
        return {
            'acousticness': np.mean([f['acousticness'] for f in valid_features]),
            'danceability': np.mean([f['danceability'] for f in valid_features]),
            'energy': np.mean([f['energy'] for f in valid_features]),
            'instrumentalness': np.mean([f['instrumentalness'] for f in valid_features]),
            'valence': np.mean([f['valence'] for f in valid_features]),
            'tempo': np.mean([f['tempo'] for f in valid_features])
        }
    
    def _get_default_targets(self) -> Dict[str, float]:
        """Get default target values when no other data is available"""
        return {
            'acousticness': 0.5,
            'danceability': 0.5,
            'energy': 0.5,
            'instrumentalness': 0.5,
            'valence': 0.5,
            'tempo': 120.0
        }
    
    def _get_seed_tracks(self, sp_client, num_seeds=5) -> List[str]:
        """Get seed tracks from liked songs and top tracks"""
        try:
            logger.info(f"Getting seed tracks for user {self.user.id}")
            
            # Get recently liked tracks
            liked_tracks = UserFeedback.objects.filter(
                user=self.user,
                feedback_type='LIKE',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).values_list('track__spotify_id', flat=True)[:num_seeds]
            
            seed_tracks = list(liked_tracks)
            logger.info(f"Found {len(seed_tracks)} liked tracks for seeds")
            
            # If we need more seeds, get from top tracks
            if len(seed_tracks) < num_seeds:
                try:
                    remaining_seeds = num_seeds - len(seed_tracks)
                    logger.info(f"Need {remaining_seeds} more seeds from top tracks")
                    top_tracks = sp_client.current_user_top_tracks(limit=remaining_seeds)
                    logger.info(f"Got {len(top_tracks['items'])} top tracks from Spotify")
                    seed_tracks.extend(track['id'] for track in top_tracks['items'])
                except Exception as e:
                    logger.error(f"Error getting top tracks for seeds: {str(e)}")
            
            logger.info(f"Final seed tracks: {seed_tracks}")
            return seed_tracks[:num_seeds] if seed_tracks else []
            
        except Exception as e:
            logger.error(f"Error getting seed tracks: {str(e)}")
            # Fall back to user's top tracks only
            try:
                top_tracks = sp_client.current_user_top_tracks(limit=num_seeds)
                return [track['id'] for track in top_tracks['items']]
            except Exception as e2:
                logger.error(f"Error getting fallback top tracks: {str(e2)}")
                return []
    
    def update_preferences(self, feedback: UserFeedback):
        """Update user preferences based on feedback"""
        try:
            if not self.preferences.feature_weights:
                self.preferences.feature_weights = {
                    'acousticness': 1.0,
                    'danceability': 1.0,
                    'energy': 1.0,
                    'instrumentalness': 1.0,
                    'valence': 1.0,
                    'tempo': 1.0
                }
            
            # Calculate adjustment based on feedback type
            adjustment_values = {
                'LIKE': 0.1,
                'SAVE': 0.15,
                'DISLIKE': -0.1,
                'SKIP': -0.05
            }
            base_adjustment = adjustment_values.get(feedback.feedback_type, 0)
            
            # Get decay factor based on feedback history
            feedback_count = UserFeedback.objects.filter(
                user=self.user,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            learning_rate = 1.0 / max(1, feedback_count)
            
            # Update weights
            for feature, value in feedback.track_features.items():
                if feature in self.preferences.feature_weights:
                    try:
                        feature_value = float(value)
                        normalized_adjustment = base_adjustment * feature_value * learning_rate
                        current_weight = float(self.preferences.feature_weights[feature])
                        new_weight = max(0.1, min(2.0, current_weight + normalized_adjustment))
                        self.preferences.feature_weights[feature] = new_weight
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Could not process feature {feature}: {str(e)}")
                        continue
            
            self.preferences.save()
            
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            raise
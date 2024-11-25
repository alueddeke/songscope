from django.db.models import Avg, F, Value, FloatField
from datetime import timedelta
from django.utils import timezone
import numpy as np
from typing import Dict, List, Optional
from .models import UserPreferences, UserFeedback, Track
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, user):
        self.user = user
        self.preferences = UserPreferences.objects.get_or_create(user=user)[0]
        
    def get_personalized_recommendations(self, sp_client, limit=20):
        """Get recommendations using personalized weights"""
        try:
            # Get user's recent feedback
            recent_feedback = UserFeedback.objects.filter(
                user=self.user,
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            """Only filtering for positive feedback (LIKE, SAVE) since we are trying to recommend similar songs, not 
            songs that the user dislikes."""

            # Filter for positive feedbacks only in recent UserFeedback
            positive_feedback = recent_feedback.filter(feedback_type__in=['LIKE', 'SAVE'])
            
            # Calculate feature targets based on positive feedback
            if positive_feedback.exists():
                targets = self._calculate_targets(positive_feedback)
                logger.info(f"Calculated targets from feedback: {targets}")
            else:
                # Fall back to user's top tracks <- Calculate average features from users top 5 tracks
                logger.info("No feedback found, falling back to top tracks")
                top_tracks = sp_client.current_user_top_tracks(limit=5)
                track_ids = [track['id'] for track in top_tracks['items']]
                audio_features = sp_client.audio_features(track_ids)
                targets = self._calculate_targets_from_features(audio_features)
            
            # Get seed tracks
            seed_tracks = self._get_seed_tracks(sp_client)
            logger.info(f"Using seed tracks: {seed_tracks}")
            
            # Add target prefix to feature names for Spotify API
            formatted_targets = {f"target_{k}": v for k, v in targets.items()}
            
            # Get recommendations from Spotify (using seed tracks and feature values in targets?)
            recommendations = sp_client.recommendations(
                seed_tracks=seed_tracks[:5],
                limit=limit,
                **formatted_targets
            )
            
            return recommendations['tracks']
            
        except Exception as e:
            logger.error(f"Error in get_personalized_recommendations: {str(e)}")
            raise
    
    def _calculate_targets(self, feedback_queryset) -> Dict[str, float]:
        """Calculate average feature values from UserFeedback.
        
        Note: This function just averages the features we care about in UserPreferences for x number of days of certain
        feedback types (like, dislike, save, skip).
        """

        try:
            # self.preferences is from UserPreferences
            features = self.preferences.feature_weights.keys() # Grab the category of feature_weights we adjust for users 
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
            return self._get_default_targets()
    
    def _calculate_targets_from_features(self, features: List[Dict]) -> Dict[str, float]:
        """Calculate average features from Spotify audio features response"""
        valid_features = [f for f in features if f is not None]
        if not valid_features:
            # If no features from top 5 user tracks are ones we care about in UserPreferences then use default target 
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
            # Get recently liked tracks
            liked_tracks = UserFeedback.objects.filter(
                user=self.user,
                feedback_type='LIKE',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).values_list('track__spotify_id', flat=True)[:num_seeds]
            
            seed_tracks = list(liked_tracks)
            
            # If we need more seeds, get from top tracks
            if len(seed_tracks) < num_seeds:
                remaining_seeds = num_seeds - len(seed_tracks)
                top_tracks = sp_client.current_user_top_tracks(limit=remaining_seeds)
                seed_tracks.extend(track['id'] for track in top_tracks['items'])
            
            return seed_tracks[:num_seeds]
            
        except Exception as e:
            logger.error(f"Error getting seed tracks: {str(e)}")
            # Fall back to user's top tracks only
            top_tracks = sp_client.current_user_top_tracks(limit=num_seeds)
            return [track['id'] for track in top_tracks['items']]
    
    def update_preferences(self, feedback: UserFeedback): # Same as UserPreferences.update_weights()?
        """Update user preferences based on feedback. Includes a learning rate based on number of feedback count in the last 30 days by user.
        
        Note: Basically same as the UserPreferences.update_weights() method but implemented into RecommendationEngine."""
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
            # The more feedback from the user, the lower the learning rate is
            learning_rate = 1.0 / max(1, feedback_count) # Should be opposite? 
            
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
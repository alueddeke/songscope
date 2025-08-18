"""
Personalization Engine - Rule-based learning from user feedback

This module implements a sophisticated rule-based system that learns from user feedback
to provide personalized music recommendations while staying compliant with Spotify's terms.

Key Concepts:
1. Rule-based learning (no ML training on Spotify data)
2. User preference analysis from feedback
3. Dynamic parameter adjustment for Spotify API
4. Time-based and context-aware personalization
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional
from django.utils import timezone
from datetime import datetime, timedelta
import json
from collections import defaultdict
import spotipy
from spotipy.exceptions import SpotifyException
from django.conf import settings
from apps.core.models import UserPreferences, UserFeedback, Track

logger = logging.getLogger(__name__)

class PersonalizationEngine:
    """
    Rule-based personalization engine that learns from user feedback.
    
    This engine analyzes user feedback patterns and adjusts recommendation
    parameters dynamically without training ML models on Spotify data.
    """
    
    def __init__(self, user):
        self.user = user
        self.preferences = UserPreferences.objects.get_or_create(user=user)[0]
        
    def analyze_user_preferences(self) -> Dict[str, Dict]:
        """
        Analyze user's feedback to build personalized preference profiles.
        
        Returns:
            Dict containing preference ranges for each audio feature
        """
        logger.info(f"Analyzing preferences for user {self.user.id}")
        
        # Get recent feedback (last 30 days for responsiveness)
        recent_feedback = UserFeedback.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if not recent_feedback.exists():
            logger.info("No recent feedback found, using default preferences")
            return self._get_default_preferences()
        
        # Separate positive and negative feedback
        positive_feedback = recent_feedback.filter(feedback_type__in=['LIKE', 'SAVE'])
        negative_feedback = recent_feedback.filter(feedback_type__in=['DISLIKE', 'SKIP'])
        
        logger.info(f"Found {positive_feedback.count()} positive and {negative_feedback.count()} negative feedback entries")
        
        # Calculate preference ranges for each audio feature
        preferences = {}
        
        # List of audio features we track
        audio_features = [
            'acousticness', 'danceability', 'energy', 'instrumentalness',
            'valence', 'tempo', 'loudness', 'speechiness', 'liveness'
        ]
        
        for feature in audio_features:
            feature_prefs = self._calculate_feature_preferences(
                feature, positive_feedback, negative_feedback
            )
            preferences[feature] = feature_prefs
            
        logger.info(f"Calculated preferences: {preferences}")
        return preferences
    
    def _calculate_feature_preferences(self, feature: str, positive_feedback, negative_feedback) -> Dict:
        """
        Calculate preference ranges for a specific audio feature.
        
        Since we can't get audio features from Spotify API, we'll use default preferences
        and learn from user feedback patterns instead.
        """
        # For now, return default preferences since we can't get audio features
        return self._get_default_feature_preferences(feature)
    
    def _get_default_feature_preferences(self, feature: str) -> Dict:
        """Get default preferences for a feature when no data is available."""
        defaults = {
            'acousticness': {'target': 0.5, 'min': 0.0, 'max': 1.0},
            'danceability': {'target': 0.5, 'min': 0.0, 'max': 1.0},
            'energy': {'target': 0.5, 'min': 0.0, 'max': 1.0},
            'instrumentalness': {'target': 0.5, 'min': 0.0, 'max': 1.0},
            'valence': {'target': 0.5, 'min': 0.0, 'max': 1.0},
            'tempo': {'target': 120.0, 'min': 60.0, 'max': 200.0},
            'loudness': {'target': -10.0, 'min': -60.0, 'max': 0.0},
            'speechiness': {'target': 0.1, 'min': 0.0, 'max': 1.0},
            'liveness': {'target': 0.1, 'min': 0.0, 'max': 1.0}
        }
        return defaults.get(feature, {'target': 0.5, 'min': 0.0, 'max': 1.0})
    
    def _get_default_preferences(self) -> Dict[str, Dict]:
        """Get default preferences when no user data is available."""
        return {
            feature: self._get_default_feature_preferences(feature)
            for feature in ['acousticness', 'danceability', 'energy', 'instrumentalness', 'valence', 'tempo']
        }
    
    def build_spotify_parameters(self, preferences: Dict) -> Dict:
        """
        Convert user preferences into Spotify API parameters.
        
        Args:
            preferences: User preference ranges for each feature
            
        Returns:
            Dict of parameters ready for Spotify recommendations API
        """
        spotify_params = {}
        
        for feature, prefs in preferences.items():
            # Add target parameters
            spotify_params[f'target_{feature}'] = prefs['target']
            
            # Add min/max parameters (only if they're meaningful)
            if prefs['min'] > 0:
                spotify_params[f'min_{feature}'] = prefs['min']
            if prefs['max'] < 1:
                spotify_params[f'max_{feature}'] = prefs['max']
        
        # Add seed tracks
        seed_tracks = self._get_seed_tracks()
        if seed_tracks:
            spotify_params['seed_tracks'] = seed_tracks[:5]  # Spotify allows max 5 seeds
        
        # Add other parameters
        spotify_params['limit'] = 20
        # Use 'market' instead of 'country' for Spotify API
        spotify_params['market'] = 'US'
        
        logger.info(f"Built Spotify parameters: {spotify_params}")
        return spotify_params
    
    def _get_seed_tracks(self) -> List[str]:
        """
        Get seed tracks based on user's liked tracks and top tracks.
        
        Returns:
            List of Spotify track IDs to use as seeds
        """
        # Get recently liked tracks
        liked_tracks = UserFeedback.objects.filter(
            user=self.user,
            feedback_type='LIKE',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('track__spotify_id', flat=True)[:3]
        
        seed_tracks = list(liked_tracks)
        
        # If we don't have enough liked tracks, we'll rely on the recommendation engine
        # to get top tracks from Spotify API
        logger.info(f"Found {len(seed_tracks)} liked tracks for seeds")
        return seed_tracks
    
    def get_time_based_adjustments(self) -> Dict:
        """
        Get time-based adjustments to preferences.
        
        This allows the system to adapt recommendations based on time of day,
        which is a common pattern in music listening.
        """
        current_hour = timezone.now().hour
        
        # Analyze what user likes at different times
        morning_feedback = UserFeedback.objects.filter(
            user=self.user,
            created_at__hour__gte=6,
            created_at__hour__lt=12,
            feedback_type__in=['LIKE', 'SAVE']
        )
        
        evening_feedback = UserFeedback.objects.filter(
            user=self.user,
            created_at__hour__gte=18,
            created_at__hour__lt=24,
            feedback_type__in=['LIKE', 'SAVE']
        )
        
        # Calculate time-based preferences
        adjustments = {}
        
        if current_hour < 12:  # Morning
            if morning_feedback.exists():
                # User has morning preferences, apply them
                adjustments = self._calculate_time_adjustments(morning_feedback, 'morning')
        elif current_hour >= 18:  # Evening
            if evening_feedback.exists():
                # User has evening preferences, apply them
                adjustments = self._calculate_time_adjustments(evening_feedback, 'evening')
        
        return adjustments
    
    def _calculate_time_adjustments(self, feedback, time_period: str) -> Dict:
        """
        Calculate adjustments based on time-specific feedback.
        
        Args:
            feedback: QuerySet of feedback for specific time period
            time_period: 'morning' or 'evening'
            
        Returns:
            Dict of adjustments to apply to preferences
        """
        adjustments = {}
        
        # Analyze energy and valence patterns for different times
        energy_values = []
        valence_values = []
        
        for fb in feedback:
            if fb.track_features:
                if 'energy' in fb.track_features:
                    energy_values.append(fb.track_features['energy'])
                if 'valence' in fb.track_features:
                    valence_values.append(fb.track_features['valence'])
        
        if energy_values:
            avg_energy = np.mean(energy_values)
            adjustments['energy'] = {
                'target': avg_energy,
                'weight': 1.2  # Give more weight to time-based preferences
            }
        
        if valence_values:
            avg_valence = np.mean(valence_values)
            adjustments['valence'] = {
                'target': avg_valence,
                'weight': 1.2
            }
        
        logger.info(f"Calculated {time_period} adjustments: {adjustments}")
        return adjustments
    
    def apply_feedback_learning(self, feedback: UserFeedback):
        """
        Update user preferences based on new feedback.
        
        This is the core learning mechanism that adapts the system
        based on user interactions.
        
        Args:
            feedback: New user feedback to learn from
        """
        logger.info(f"Learning from feedback: {feedback.feedback_type} for track {feedback.track.name}")
        
        # Update the user preferences model
        if feedback.track_features:
            self.preferences.update_weights(feedback, feedback.track_features)
        
        # Log the learning event
        logger.info(f"Updated preferences for user {self.user.id} based on {feedback.feedback_type}")
    
    def remove_feedback_learning(self, track_id: str):
        """
        Remove learning effects when a user unlikes a track.
        
        Args:
            track_id: Spotify track ID to remove feedback for
        """
        logger.info(f"Removing feedback learning for track {track_id}")
        
        # Find and remove the feedback entry
        try:
            track = Track.objects.get(spotify_id=track_id)
            feedback = UserFeedback.objects.filter(
                user=self.user,
                track=track,
                feedback_type='LIKE'
            ).first()
            
            if feedback:
                # Remove the feedback entry
                feedback.delete()
                logger.info(f"Removed LIKE feedback for track {track.name}")
                
                # Optionally, we could reverse the learning effects here
                # For now, we just remove the feedback entry
                
        except Track.DoesNotExist:
            logger.warning(f"Track {track_id} not found when removing feedback")
        except Exception as e:
            logger.error(f"Error removing feedback learning: {str(e)}")
    
    def get_personalization_summary(self) -> Dict:
        """
        Get a summary of the user's personalization profile.
        
        This is useful for debugging and understanding how the system
        is personalizing for each user.
        """
        preferences = self.analyze_user_preferences()
        
        # Count feedback by type
        feedback_counts = UserFeedback.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values('feedback_type').annotate(count=Count('feedback_type'))
        
        summary = {
            'user_id': self.user.id,
            'preferences': preferences,
            'feedback_summary': {item['feedback_type']: item['count'] for item in feedback_counts},
            'total_feedback': sum(item['count'] for item in feedback_counts),
            'last_updated': self.preferences.updated_at.isoformat()
        }
        
        return summary 
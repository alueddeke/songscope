from django.db.models import Avg
from datetime import timedelta
from django.utils import timezone
import numpy as np
from typing import Dict, List, Optional

class RecommendationEngine:
    def __init__(self, user):
        self.user = user
        self.preferences = UserPreferences.objects.get_or_create(user=user)[0]
        
    def get_personalized_recommendations(self, sp_client, limit=20):
        """Get recommendations using personalized weights"""
        # Get user's recent feedback
        recent_feedback = UserFeedback.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        # Calculate feature targets based on positive feedback
        positive_feedback = recent_feedback.filter(feedback_type__in=['LIKE', 'SAVE'])
        if positive_feedback.exists():
            targets = self._calculate_targets(positive_feedback)
        else:
            # Fall back to user's top tracks if no feedback
            top_tracks = sp_client.current_user_top_tracks(limit=5)
            targets = self._extract_features_from_tracks(sp_client, top_tracks['items'])
        
        # Apply user's feature weights
        weighted_targets = self._apply_weights(targets)
        
        # Get seed tracks from recent likes and top tracks
        seed_tracks = self._get_seed_tracks(sp_client)
        
        # Get recommendations from Spotify
        recommendations = sp_client.recommendations(
            seed_tracks=seed_tracks[:5],
            limit=limit,
            **weighted_targets
        )
        
        return recommendations['tracks']
    
    def _calculate_targets(self, feedback_queryset) -> Dict[str, float]:
        """Calculate average features from feedback"""
        return {
            feature: feedback_queryset.aggregate(
                Avg(f'track_features__{feature}')
            )[f'track_features__{feature}__avg']
            for feature in self.preferences.feature_weights.keys()
        }
    
    def _apply_weights(self, targets: Dict[str, float]) -> Dict[str, float]:
        """Apply user's feature weights to target values"""
        weighted_targets = {}
        for feature, value in targets.items():
            if feature in self.preferences.feature_weights:
                weight = self.preferences.feature_weights[feature]
                weighted_targets[f'target_{feature}'] = value * weight
        return weighted_targets
    
    def _extract_features_from_tracks(self, sp_client, tracks: List[Dict]) -> Dict[str, float]:
        """Extract average audio features from a list of tracks"""
        track_ids = [track['id'] for track in tracks]
        features = sp_client.audio_features(track_ids)
        
        return {
            feature: np.mean([track[feature] for track in features if track])
            for feature in self.preferences.feature_weights.keys()
        }
    
    def _get_seed_tracks(self, sp_client, num_seeds=5) -> List[str]:
        """Get seed tracks from liked songs and top tracks"""
        # Get recently liked tracks
        liked_tracks = UserFeedback.objects.filter(
            user=self.user,
            feedback_type='LIKE',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('track__spotify_id', flat=True)[:num_seeds]
        
        # If we need more seeds, get from top tracks
        if len(liked_tracks) < num_seeds:
            top_tracks = sp_client.current_user_top_tracks(
                limit=num_seeds - len(liked_tracks)
            )
            liked_tracks.extend(track['id'] for track in top_tracks['items'])
        
        return list(liked_tracks)[:num_seeds]
    
    def update_preferences(self, feedback: UserFeedback):
        """Update user preferences based on feedback"""
        # Update feature weights
        self._update_feature_weights(feedback)
        
        # Update genre preferences
        self._update_genre_preferences(feedback)
        
        self.preferences.save()
    
    def _update_feature_weights(self, feedback: UserFeedback):
        """Update feature weights based on feedback"""
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
        
        # Apply adjustments with decay based on historical feedback
        recent_feedback = UserFeedback.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        feedback_count = recent_feedback.count()
        learning_rate = 1.0 / max(1, feedback_count)  # Decrease impact as we get more feedback
        
        for feature, value in feedback.track_features.items():
            if feature in self.preferences.feature_weights:
                # Calculate normalized adjustment
                normalized_adjustment = base_adjustment * value * learning_rate
                
                # Update weight with bounds
                current_weight = self.preferences.feature_weights[feature]
                new_weight = current_weight + normalized_adjustment
                self.preferences.feature_weights[feature] = max(0.1, min(2.0, new_weight))
    
    def _update_genre_preferences(self, feedback: UserFeedback):
        """Update genre preferences based on feedback"""
        if not self.preferences.genre_preferences:
            self.preferences.genre_preferences = {}
            
        # Get track's genres from artist
        track = Track.objects.get(spotify_id=feedback.track.spotify_id)
        genres = track.genres
        
        # Calculate adjustment
        adjustment = {
            'LIKE': 1,
            'SAVE': 2,
            'DISLIKE': -1,
            'SKIP': -0.5
        }.get(feedback.feedback_type, 0)
        
        # Update genre preferences
        for genre in genres:
            current_score = self.preferences.genre_preferences.get(genre, 0)
            self.preferences.genre_preferences[genre] = max(0, current_score + adjustment)
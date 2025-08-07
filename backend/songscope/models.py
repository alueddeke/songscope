from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import time


# DB could be for OAuth tokens, consistent user states, user interactions etc...

#Spotify Token
class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_type = models.CharField(max_length=50)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_in = models.IntegerField()
    
    def is_expired(self):
        return self.expires_at <= timezone.now()
    
    def update_token_info(self, access_token, refresh_token, expires_in):
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        self.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        self.expires_in = expires_in
        self.save()

    def __str__(self):
        return f"{self.user.username}'s Spotify Token"



#potential models that could help:

#Track info to store
class Track(models.Model):
    spotify_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255)
    popularity = models.IntegerField(default=0)
    genres = models.JSONField(default=list)  
    audio_features = models.JSONField(null=True, blank=True)  
    duration_ms = models.IntegerField(null=True, blank=True) 
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.artist}"

    def update_features(self, features_data):
   
        self.audio_features = features_data
        self.save()


class UserFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    feedback_type = models.CharField(
        max_length=10,
        choices=[
            ('LIKE', 'Like'),
            ('DISLIKE', 'Dislike'),
            ('SKIP', 'Skip'),
            ('SAVE', 'Save'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Store audio features at the time of feedback for learning
    track_features = models.JSONField(null=True, blank=True)


class AIFeedback(models.Model):
    """Store AI-interpreted feedback from natural language"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, null=True, blank=True)
    original_text = models.TextField()  # User's original feedback text
    interpretation = models.JSONField()  # AI interpretation
    confidence = models.FloatField(default=0.0)  # AI confidence score
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Feedback for {self.user.username} - {self.original_text[:50]}"


class UserPreferences(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Weights for different audio features
    feature_weights = models.JSONField(default=dict)
    genre_preferences = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def update_weights(self, feedback, track_features):
        """Update weights based on user feedback"""
        if not self.feature_weights:
            self.feature_weights = {
                'acousticness': 1.0,
                'danceability': 1.0,
                'energy': 1.0,
                'instrumentalness': 1.0,
                'valence': 1.0,
                'tempo': 1.0
            }
        
        # Adjust weights based on feedback type
        adjustment = {
            'LIKE': 0.1,   # Increase weight for liked features
            'DISLIKE': -0.1,  # Decrease weight for disliked features
            'SAVE': 0.15,   # Strong positive signal
            'SKIP': -0.05   # Mild negative signal
        }.get(feedback.feedback_type, 0)

        # Update weights for each feature
        for feature, value in track_features.items():
            if feature in self.feature_weights:
                # Normalize the adjustment based on feature value
                normalized_adjustment = adjustment * value
                self.feature_weights[feature] = max(0.1, min(2.0, 
                    self.feature_weights[feature] + normalized_adjustment))
        
        self.save()

#Recommendation Log
class RecommendationLog(models.Model):
    ACTION_CHOICES = [
        ('RECOMMENDED', 'Recommendation Generated'),
        ('ERROR', 'Error Occurred'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey('Track', on_delete=models.CASCADE, null=True, blank=True)  # Optional because errors might not have tracks
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    error_message = models.TextField(null=True, blank=True)  # Only used when action is 'ERROR'

    class Meta:
        # Only keep logs from last 7 days
        indexes = [
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        if self.action == 'ERROR':
            return f"Error for {self.user.username} at {self.timestamp}: {self.error_message[:50]}"
        return f"Recommendation for {self.user.username}: {self.track.name if self.track else 'No track'}"

    @classmethod
    def log_error(cls, user, error_message):
        """Helper method to log errors"""
        return cls.objects.create(
            user=user,
            action='ERROR',
            error_message=error_message
        )

    @classmethod
    def log_recommendation(cls, user, track):
        """Helper method to log successful recommendations"""
        return cls.objects.create(
            user=user,
            track=track,
            action='RECOMMENDED'
        )

class UserProfile(models.Model):
    """
    Stores user-specific recommendation data and preferences.
    Uses JSON field for flexible data storage while maintaining structure.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    data = models.JSONField(default=dict)
    recommendation_cache = models.JSONField(default=list)  # Store up to 50 recommendations
    cache_last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    @property
    def is_fresh(self):
        """Check if profile data is fresh (less than 1 day old)"""
        from django.utils import timezone
        from datetime import timedelta
        return self.updated_at > timezone.now() - timedelta(days=1)
    
    def needs_update(self):
        """Check if profile needs updating (more than 1 day old)"""
        return not self.is_fresh
    
    def add_feedback(self, track_id, feedback_type, track_info=None):
        """Add user feedback to profile"""
        if 'preferences' not in self.data:
            self.data['preferences'] = {}
        if 'feedback_history' not in self.data['preferences']:
            self.data['preferences']['feedback_history'] = []
        
        feedback_entry = {
            'track_id': track_id,
            'feedback_type': feedback_type,
            'timestamp': timezone.now().isoformat()
        }
        
        if track_info:
            feedback_entry['track_info'] = track_info
        
        self.data['preferences']['feedback_history'].append(feedback_entry)
        
        # Update liked/disliked artists based on feedback
        if track_info and 'artist' in track_info:
            if feedback_type == 'LIKE':
                if 'liked_artists' not in self.data['preferences']:
                    self.data['preferences']['liked_artists'] = []
                if track_info['artist'] not in self.data['preferences']['liked_artists']:
                    self.data['preferences']['liked_artists'].append(track_info['artist'])
            elif feedback_type == 'DISLIKE':
                if 'disliked_artists' not in self.data['preferences']:
                    self.data['preferences']['disliked_artists'] = []
                if track_info['artist'] not in self.data['preferences']['disliked_artists']:
                    self.data['preferences']['disliked_artists'].append(track_info['artist'])
        
        self.save()
    
    def get_recommendation_weights(self):
        """Get current recommendation weights"""
        return self.data.get('recommendation_weights', {
            'playlist_mining': 0.3,
            'artist_network': 0.25,
            'contextual': 0.2,
            'popularity': 0.15,
            'feedback': 0.1
        })
    
    def update_weights(self, new_weights):
        """Update recommendation weights"""
        self.data['recommendation_weights'] = new_weights
        self.save()
    
    def add_to_cache(self, recommendations):
        """Add new recommendations to cache (max 50)"""
        # Add new recommendations to the beginning
        self.recommendation_cache = recommendations + self.recommendation_cache
        
        # Keep only the first 50
        if len(self.recommendation_cache) > 50:
            self.recommendation_cache = self.recommendation_cache[:50]
        
        # Reset position to 0 to start from the NEW recommendations
        # This ensures user sees fresh tracks first
        self.data['cache_position'] = 0
        
        self.cache_last_updated = timezone.now()
        self.save()
    
    def get_from_cache(self, count=10):
        """Get recommendations from cache using sliding window"""
        if not self.recommendation_cache:
            return []
        
        # Use a sliding window approach to cycle through different tracks
        # Get the current position from the data field
        current_position = self.data.get('cache_position', 0)
        
        # If position is beyond cache size, reset to beginning
        if current_position >= len(self.recommendation_cache):
            current_position = 0
            self.data['cache_position'] = 0
        
        # Calculate the end position
        end_position = current_position + count
        
        # If we need to wrap around, get tracks from beginning
        if end_position > len(self.recommendation_cache):
            # Get remaining tracks from current position
            remaining = self.recommendation_cache[current_position:]
            # Get tracks from beginning to fill the rest
            needed = count - len(remaining)
            from_beginning = self.recommendation_cache[:needed]
            result = remaining + from_beginning
            # Update position to where we ended
            self.data['cache_position'] = needed
        else:
            # Get tracks from current position
            result = self.recommendation_cache[current_position:end_position]
            # Update position
            self.data['cache_position'] = end_position
        
        self.save()
        return result
    
    def is_cache_fresh(self, max_age_hours=1):
        """Check if cache is fresh (less than max_age_hours old)"""
        from datetime import timedelta
        return self.cache_last_updated > timezone.now() - timedelta(hours=max_age_hours)
    
    def cache_size(self):
        """Get current cache size"""
        return len(self.recommendation_cache)
    
    def get_cache_stats(self):
        """Get cache statistics for debugging"""
        current_position = self.data.get('cache_position', 0)
        return {
            'cache_size': len(self.recommendation_cache),
            'current_position': current_position,
            'tracks_remaining': len(self.recommendation_cache) - current_position,
            'has_wrapped': current_position >= len(self.recommendation_cache)
        }
    
    def reset_cache_position(self):
        """Reset cache position to beginning"""
        self.data['cache_position'] = 0
        self.save()
    
    def clear_cache(self):
        """Clear all cached recommendations"""
        self.recommendation_cache = []
        self.data['cache_position'] = 0
        self.save()
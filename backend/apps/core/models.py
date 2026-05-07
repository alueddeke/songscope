"""
Core models for SongScope application

This module contains the core models for user management and basic functionality.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SpotifyToken(models.Model):
    """Model to store Spotify OAuth tokens for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        """Check if the token is expired"""
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Spotify Token for {self.user.username}"


class UserProfile(models.Model):
    """Extended user profile with music preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    spotify_user_id = models.CharField(max_length=255, blank=True, null=True)
    favorite_genres = models.JSONField(default=list, blank=True)
    favorite_artists = models.JSONField(default=list, blank=True)
    data = models.JSONField(default=dict, blank=True)  # Store profile data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def get_from_cache(self, limit=20):
        """Get recommendations from cache"""
        try:
            cache_data = self.data.get('cache', {})
            if cache_data and cache_data.get('recommendations'):
                return cache_data['recommendations'][:limit]
            return None
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    def get_cache_stats(self):
        """Get cache statistics"""
        try:
            cache_data = self.data.get('cache', {})
            return {
                'has_cache': bool(cache_data.get('recommendations')),
                'cache_size': len(cache_data.get('recommendations', [])),
                'last_updated': cache_data.get('last_updated'),
                'cache_hits': cache_data.get('hits', 0),
                'cache_misses': cache_data.get('misses', 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear the recommendation cache"""
        try:
            if 'cache' in self.data:
                self.data['cache'] = {}
                self.save(update_fields=['data'])
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    def update_cache(self, recommendations):
        """Update the recommendation cache"""
        try:
            if 'cache' not in self.data:
                self.data['cache'] = {}
            
            self.data['cache']['recommendations'] = recommendations
            self.data['cache']['last_updated'] = timezone.now().isoformat()
            self.save(update_fields=['data'])
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}")
    
    def add_feedback(self, track_id, feedback_type, track_info=None):
        """Add feedback to the user's profile data"""
        try:
            if 'feedback_history' not in self.data:
                self.data['feedback_history'] = []
            
            feedback_entry = {
                'track_id': track_id,
                'feedback_type': feedback_type,
                'timestamp': timezone.now().isoformat(),
                'track_info': track_info or {}
            }
            
            self.data['feedback_history'].append(feedback_entry)
            
            # Keep only last 100 feedback entries to prevent data bloat
            if len(self.data['feedback_history']) > 100:
                self.data['feedback_history'] = self.data['feedback_history'][-100:]
            
            self.save(update_fields=['data'])
            logger.info(f"Added feedback to profile: {feedback_type} for track {track_id}")
        except Exception as e:
            logger.error(f"Error adding feedback to profile: {str(e)}")
    
    def remove_feedback(self, track_id):
        """Remove feedback for a specific track"""
        try:
            if 'feedback_history' in self.data:
                self.data['feedback_history'] = [
                    f for f in self.data['feedback_history'] 
                    if f.get('track_id') != track_id
                ]
                self.save(update_fields=['data'])
                logger.info(f"Removed feedback for track {track_id}")
        except Exception as e:
            logger.error(f"Error removing feedback: {str(e)}")


class Track(models.Model):
    """Model to store track information"""
    spotify_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255, blank=True)
    duration_ms = models.IntegerField(default=0)
    popularity = models.IntegerField(default=0)
    genres = models.JSONField(default=list, blank=True)  # Store artist genres
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.artist}"


class UserFeedback(models.Model):
    """Model to store user feedback on tracks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    feedback_text = models.TextField(blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    liked = models.BooleanField(null=True, blank=True)
    feedback_type = models.CharField(max_length=20, choices=[
        ('LIKE', 'Like'),
        ('DISLIKE', 'Dislike'),
        ('SAVE', 'Save'),
        ('SKIP', 'Skip'),
        ('PLAY', 'Play')
    ], blank=True)
    track_features = models.JSONField(default=dict, blank=True)  # Store track audio features
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'track']

    def __str__(self):
        return f"Feedback from {self.user.username} on {self.track.name}"


class UserPreferences(models.Model):
    """Model to store user music preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_genres = models.JSONField(default=list, blank=True)
    preferred_artists = models.JSONField(default=list, blank=True)
    preferred_tempo_range = models.JSONField(default=dict, blank=True)
    preferred_energy_level = models.CharField(max_length=20, blank=True)
    preferred_mood = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"


class AIFeedback(models.Model):
    """Model to store AI-generated feedback interpretations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    original_feedback = models.TextField()
    ai_interpretation = models.JSONField()
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Feedback for {self.user.username} on {self.track.name}"


class RecommendationLog(models.Model):
    """Log of track recommendations for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    recommended_at = models.DateTimeField(auto_now_add=True)
    feedback = models.CharField(max_length=255, blank=True)
    liked = models.BooleanField(null=True, blank=True)
    track_popularity = models.IntegerField(default=0)
    was_novel = models.BooleanField(default=True)

    class Meta:
        ordering = ['-recommended_at']

    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.track.name}"
    
    @classmethod
    def log_recommendation(cls, user, track):
        """Log a track recommendation"""
        try:
            cls.objects.create(user=user, track=track)
        except Exception as e:
            logger.error(f"Error logging recommendation: {str(e)}")
    
    @classmethod
    def log_error(cls, user, error_message):
        """Log an error during recommendation generation"""
        try:
            # Create a dummy track for error logging
            track, _ = Track.objects.get_or_create(
                spotify_id='error_log',
                defaults={'name': 'Error Log', 'artist': 'System', 'album': 'Error'}
            )
            cls.objects.create(
                user=user,
                track=track,
                feedback=f"Error: {error_message}"
            )
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")


class DailyGem(models.Model):
    """One recommended track per user per day — the core horoscope feature."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    explanation = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    preview_url = models.URLField(max_length=500, blank=True)
    track_popularity = models.IntegerField(default=0)
    was_liked = models.BooleanField(null=True, blank=True)
    was_skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Daily Gem for {self.user.username} on {self.date}: {self.track.name}"

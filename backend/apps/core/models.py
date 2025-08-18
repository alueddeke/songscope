"""
Core models for SongScope application

This module contains the core models for user management and basic functionality.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class Track(models.Model):
    """Model to store track information"""
    spotify_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255, blank=True)
    duration_ms = models.IntegerField(default=0)
    popularity = models.IntegerField(default=0)
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

    class Meta:
        ordering = ['-recommended_at']

    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.track.name}"

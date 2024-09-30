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
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_expired(self):
        return self.expires_at <= timezone.now()
    
    def update_token_info(self, access_token, refresh_token, expires_in):
        self.access_token = access_token
        if refresh_token:  # Only update if a new refresh token is provided
            self.refresh_token = refresh_token
        self.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        self.save()

    def __str__(self):
        return f"{self.user.username}'s Spotify Token"

#Track info to store
class Track(models.Model):
    spotify_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255)
    duration_ms = models.IntegerField()
    popularity = models.IntegerField()
    added_at = models.DateTimeField(auto_now_add=True)


#Recommendation Log
class RecommendationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    recommended_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)  # e.g., 'played', 'skipped'

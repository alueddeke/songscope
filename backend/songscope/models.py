from django.db import models
from django.contrib.auth.models import User


# DB could be for OAuth tokens, consistent user states, user interactions etc...

#Spotify Token
class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_type = models.CharField(max_length=50)
    expires_in = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

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

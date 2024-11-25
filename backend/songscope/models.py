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
    """Captures and stores user feedback based on specific tracks."""
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
    track_features = models.JSONField(null=True, blank=True) # Inherit audio features of the song the user gives feedback to


class UserPreferences(models.Model):
    # Grabbing everything needed from the Django database first
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    # Weights for different audio features
    feature_weights = models.JSONField(default=dict) # Looking for this in the Django database first, if don't have create empty dict
    genre_preferences = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def update_weights(self, feedback, track_features):
        """Update feature_weights database based on user feedback."""
        if not self.feature_weights:

            # REMINDER: feature_weights not the same as track_feature values
            self.feature_weights = {
                'acousticness': 1.0, # Should the weights be normalized to 1 here? 
                'danceability': 1.0,
                'energy': 1.0,
                'instrumentalness': 1.0,
                'valence': 1.0,
                'tempo': 1.0
            }
        
        # Adjust weights based on feedback type (ADJUSTMENT IN PERCENTAGE)
        adjustment = {
            'LIKE': 0.1,   # Increase weight for liked features
            'DISLIKE': -0.1,  # Decrease weight for disliked features
            'SAVE': 0.15,   # Strong positive signal
            'SKIP': -0.05   # Mild negative signal
        }.get(feedback.feedback_type, 0)

        # Update weights for each feature
        for feature, value in track_features.items(): # original values in track features can get pretty high though (tempo ~190 for some songs)
            if feature in self.feature_weights:
                """This method of weight adjustment won't be really balanced for each feature. That is we might see more effect for
                track_features that naturally have lower values, e.g. -1 < track_features < 1. This is due to the clamping operation in the last
                line of the code below, reinforcing any feature_weight adjustments to be between 0.1 and 2.0. Example: Features like tempo naturally have
                a bigger range of values, thus a value adjustment of 2.0 may not be noticeable at all."""

                # Normalize the adjustment based on feature value <- doesn't really matter what percentage of adjustment gets applied (normalized)
                # if they will get the clamping operation (specifically for unnormalized track_features, e.g. tempo) 
                normalized_adjustment = adjustment * value # Weights are adjusted according to the original song feature value in percentages 

                # Should add an if 
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
from django.contrib.auth.models import User, Group
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):
    # inherit from hyperlink model, using a hyperlink/url instead of typical primary key relationship
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']

    
class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model= Group
        fields = ['url', 'name']



class AudioFeaturesSerializer(serializers.Serializer):
    acousticness = serializers.FloatField()
    instrumentalness = serializers.FloatField()
    energy = serializers.FloatField()
    valence = serializers.FloatField()
    danceability = serializers.FloatField()
    tempo = serializers.FloatField()
    loudness = serializers.FloatField()
    duration_ms = serializers.FloatField()
    liveness = serializers.FloatField()
    key = serializers.FloatField()
    mode = serializers.FloatField()

class UserProfileSerializer(serializers.Serializer):
    weighted_features = AudioFeaturesSerializer()
    top_genres = serializers.ListField(
        child=serializers.ListField(
            child=serializers.CharField()
        )
    )
    top_artists = serializers.ListField(
        child=serializers.ListField(
            child=serializers.CharField()
        )
    )
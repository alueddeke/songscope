# backend/myapp/views.py

from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from songscope.serializers import UserSerializer, GroupSerializer

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from requests_oauthlib import OAuth2Session
from django.contrib.auth.decorators import login_required
from .utils import generate_code_verifier, generate_code_challenge, update_or_create_user_tokens, get_user_tokens

client_id = settings.SPOTIFY_CLIENT_ID
redirect_uri = settings.REDIRECT_URI
scope = 'user-read-private user-read-email user-library-read'

#get,post, delete etc... 
#viewset can combine these into less code

class UserViewSet(viewsets.ModelViewSet):
    #api endpoint - create users, view all users, view one user, delete users
    queryset= User.objects.all().order_by('-date_joined')  
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
class GroupViewSet(viewsets.ModelViewSet):
    queryset= Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


def spotify_login(request):
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    request.session['code_verifier'] = verifier

    spotify = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorization_url, state = spotify.authorization_url(
        'https://accounts.spotify.com/authorize',
        code_challenge=challenge,
        code_challenge_method='S256'
    )
    request.session['oauth_state'] = state
    return HttpResponseRedirect(authorization_url)

def spotify_callback(request):
    verifier = request.session.get('code_verifier')
    spotify = OAuth2Session(client_id, redirect_uri=redirect_uri, state=request.session['oauth_state'])
    token = spotify.fetch_token(
        'https://accounts.spotify.com/api/token',
        authorization_response=request.build_absolute_uri(),
        client_id=client_id,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        code_verifier=verifier
    )
    update_or_create_user_tokens(request.user, token['access_token'], token['token_type'], token['expires_in'], token['refresh_token'])
    return HttpResponseRedirect(reverse('user_profile'))

@login_required
def user_profile(request):
    token = get_user_tokens(request.user)
    if not token:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    spotify = OAuth2Session(client_id, token={
        'access_token': token.access_token,
        'refresh_token': token.refresh_token,
        'token_type': token.token_type,
        'expires_in': token.expires_in
    })
    response = spotify.get('https://api.spotify.com/v1/me')
    return JsonResponse(response.json())


@login_required
def get_user_playlists(request):
    token = get_user_tokens(request.user)
    if not token:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    spotify = OAuth2Session(client_id, token={
        'access_token': token.access_token,
        'refresh_token': token.refresh_token,
        'token_type': token.token_type,
        'expires_in': token.expires_in
    })
    response = spotify.get('https://api.spotify.com/v1/me/playlists')
    return JsonResponse(response.json())
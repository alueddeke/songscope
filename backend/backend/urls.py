"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from songscope import views
from songscope.views import spotify_login, spotify_callback, user_profile

# this is where you would define routes - your get one, post one, etc...
# if you register your viewset to routers, it does all this for you
# less code but good for most cases, if you need more control, do it manually
router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('login/', spotify_login, name='spotify-login'),
    path('callback/', spotify_callback, name='spotify-callback'),
    path('profile/', user_profile, name='user-profile'),
    path('api/user-playlists/', views.get_user_playlists, name='user_playlists'),
]

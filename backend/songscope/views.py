from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from songscope.serializers import UserSerializer, GroupSerializer

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


from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_number']  # you can expand later if needed


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)  #  nested serializer
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class AdminUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)  #  show phone number to admin
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'is_active', 'is_staff', 'profile']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'due_date', 'is_completed', 'user']
        read_only_fields = ['id', 'user']

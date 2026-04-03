
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Task, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'is_premium']


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
    due_time = serializers.TimeField(
        required=False,
        input_formats=["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"],
    )

    class Meta:
        model = Task
        fields = ['id', 'title', 'due_date', 'due_time', 'is_completed', 'user', 'updated_at']
        read_only_fields = ['id', 'user', 'updated_at']


class ProfileDetailSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="profile.phone_number", allow_blank=True, allow_null=True)
    is_premium = serializers.BooleanField(source="profile.is_premium", read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'is_premium', 'date_joined']
        read_only_fields = ['id', 'is_premium', 'date_joined']


class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, max_length=150)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=15)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required.")
        return attrs

    def validate_username(self, value):
        request = self.context["request"]
        if User.objects.filter(username=value).exclude(pk=request.user.pk).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        request = self.context["request"]
        if User.objects.filter(email__iexact=value).exclude(pk=request.user.pk).exists():
            raise serializers.ValidationError("Email already exists.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        current_password = attrs.get("current_password")
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")

        if not user.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})

        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs

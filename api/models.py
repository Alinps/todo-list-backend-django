from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from datetime import time as datetime_time

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    due_time = models.TimeField(default=datetime_time(9, 0))
    is_completed = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_premium = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.user.username}'s Profile"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create Task'),
        ('update', 'Update Task'),
        ('delete', 'Delete Task'),
        ('complete_true', 'Mark Complete'),
        ('complete_false', 'Mark Incomplete'),
        ('import', 'Import Tasks'),
        ('export', 'Export Tasks'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.message}"

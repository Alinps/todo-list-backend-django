# myapp/tasks.py
from datetime import date, timedelta
from .models import Task, Notification
from django.contrib.auth.models import User

def send_due_tomorrow_notifications():
    tomorrow = date.today() + timedelta(days=1)
    for user in User.objects.all():
        tasks = Task.objects.filter(
            due_date=tomorrow,
            is_completed=False,
            user=user
        )
        for task in tasks:
            Notification.objects.create(
                user=user,
                message=f"Task '{task.title}' is due tomorrow!"
            )

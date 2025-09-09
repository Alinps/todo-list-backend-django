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


# tasks.py
import time
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Task


def check_due_tasks():
    """Continuously check for due tasks and send notifications."""
    while True:
        now = timezone.now()
        due_tasks = Task.objects.filter(due_date__lte=now, completed=False, notified=False)

        for task in due_tasks:
            send_mail(
                subject=f"Task Due: {task.title}",
                message=f"Hi {task.user.username}, your task '{task.title}' is now due!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[task.user.email],
                fail_silently=False,
            )

            task.notified = True
            task.save()

        time.sleep(60)  # checks every minute

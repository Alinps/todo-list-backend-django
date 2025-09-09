# api/tasks_checker.py
import time
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Task  # Adjust import based on your app structure

def check_due_tasks():
    """Continuously check for due tasks and send notifications"""
    while True:
        now = timezone.now()

        # Filter tasks that are due and not completed or notified
        due_tasks = Task.objects.filter(due_date__lte=now, completed=False, notified=False)

        for task in due_tasks:
            # Send email notification
            send_mail(
                subject=f"Task Due: {task.title}",
                message=f"Hi {task.user.username}, your task '{task.title}' is now due!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[task.user.email],
                fail_silently=False,
            )

            # Mark as notified
            task.notified = True
            task.save()

        time.sleep(60)  # check every minute

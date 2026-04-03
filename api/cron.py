import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification, Task
from .utils.sms_service import send_sms


logger = logging.getLogger(__name__)


def remind_due_tasks():
    """
    Sends one reminder per task due tomorrow through:
    - in-app notification (Notification model)
    - SMS (if phone number is available)
    - email (if user email is available)

    Idempotency:
    Uses Notification.get_or_create on a stable message format so repeated cron runs
    do not resend duplicate reminders for the same task.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    tasks = Task.objects.select_related("user").filter(
        due_date=tomorrow,
        is_completed=False,
    )

    sent_count = 0
    skipped_existing = 0
    skipped_no_contact = 0

    for task in tasks:
        user = task.user
        reminder_message = (
            f"Reminder: Task '{task.title}' (ID: {task.id}) is due on {task.due_date:%Y-%m-%d}."
        )

        notification, created = Notification.objects.get_or_create(
            user=user,
            message=reminder_message,
        )
        if not created:
            skipped_existing += 1
            continue

        sent_count += 1

        # SMS channel (optional)
        phone_number = None
        profile = getattr(user, "profile", None)
        if profile is not None:
            phone_number = getattr(profile, "phone_number", None)
        if phone_number:
            send_sms(phone_number, reminder_message)
        else:
            skipped_no_contact += 1

        # Email channel (optional)
        if user.email:
            send_mail(
                subject=f"Task Reminder: {task.title}",
                message=reminder_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        else:
            skipped_no_contact += 1

        logger.info(
            "cron.reminder.sent user=%s task_id=%s notification_id=%s",
            user.username,
            task.id,
            notification.id,
        )

    logger.info(
        "cron.reminder.summary due_tomorrow=%s sent=%s skipped_existing=%s skipped_no_contact=%s",
        tasks.count(),
        sent_count,
        skipped_existing,
        skipped_no_contact,
    )

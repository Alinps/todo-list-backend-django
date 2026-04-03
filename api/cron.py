import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification, Task
from .utils.sms_service import send_sms


logger = logging.getLogger(__name__)


def remind_due_tasks():
    """
    Sends one reminder per task when its due date-time is reached through:
    - in-app notification (Notification model)
    - SMS (if phone number is available)
    - email (if user email is available)

    Idempotency:
    Uses Task.notified so repeated cron runs do not resend duplicate reminders.
    """
    now = timezone.now()
    tasks = Task.objects.select_related("user").filter(
        is_completed=False,
        notified=False,
    )

    sent_count = 0
    skipped_not_due_yet = 0
    skipped_no_contact = 0

    for task in tasks:
        due_naive = datetime.combine(task.due_date, task.due_time)
        due_at = timezone.make_aware(due_naive, timezone.get_current_timezone())
        if due_at > now:
            skipped_not_due_yet += 1
            continue

        user = task.user
        reminder_message = (
            f"Task '{task.title}' (ID: {task.id}) is due at {due_at:%Y-%m-%d %H:%M}." # type: ignore
        )

        notification = Notification.objects.create(
            user=user,
            message=reminder_message,
        )

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
            task.id, # type: ignore
            notification.id, # type: ignore
        )
        task.notified = True
        task.save(update_fields=["notified"])

    logger.info(
        "cron.reminder.summary pending=%s sent=%s skipped_not_due_yet=%s skipped_no_contact=%s",
        tasks.count(),
        sent_count,
        skipped_not_due_yet,
        skipped_no_contact,
    )

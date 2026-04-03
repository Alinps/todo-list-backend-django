from .utils.sms_service import send_sms

def notify_due_date(user, task):
    if not task.due_date:
        return

    profile = getattr(user, "profile", None)
    phone_number = getattr(profile, "phone_number", None)
    if not phone_number:
        return

    due_date_str = task.due_date.strftime("%d-%m-%Y")
    due_time_str = task.due_time.strftime("%H:%M") if getattr(task, "due_time", None) else "00:00"
    msg = f"Hello {user.username}, reminder: Task '{task.title}' is due on {due_date_str} at {due_time_str}."
    send_sms(phone_number, msg)

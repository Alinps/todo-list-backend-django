from .utils.sms_service import send_sms

def notify_due_date(user, task):
    if not task.due_date:
        return

    profile = getattr(user, "profile", None)
    phone_number = getattr(profile, "phone_number", None)
    if not phone_number:
        return

    due_date_str = task.due_date.strftime("%d-%m-%Y")
    msg = f"Hello {user.username}, reminder: Task '{task.title}' is due on {due_date_str}."
    send_sms(phone_number, msg)

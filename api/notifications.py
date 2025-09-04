from utils.sms_service import send_sms
from datetime import datetime
from models import Task

def notify_due_date(user, task):
    if task.due_date:
        due_date_str = task.due_date.strftime("%d-%m-%Y %H:%M")
        msg = f"Hello {user.username}, reminder: Task '{task.title}' is due on {due_date_str}."
        send_sms(user.phone_number, msg)   # assumes you stored phone_number in User model

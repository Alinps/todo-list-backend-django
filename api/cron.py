# tasks/cron.py
from datetime import datetime, timedelta
from .models import Task
from utils.sms_service import send_sms

def remind_due_tasks():
    with open("cron_test_log.txt", "a") as f:
        f.write(f"Cron job executed at {datetime.now()}\n")
    print("Cron job triggered!")
    upcoming = datetime.now() + timedelta(days=1)
    tasks = Task.objects.filter(due_date__date=upcoming.date())
    for task in tasks:
        user = task.user
        msg = f"Reminder: '{task.title}' is due tomorrow!"
        send_sms(user.phone_number, msg)

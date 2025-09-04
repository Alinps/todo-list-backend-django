# myapp/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import send_due_tomorrow_notifications

def start():
    scheduler = BackgroundScheduler()
    # Run every minutes
    scheduler.add_job(send_due_tomorrow_notifications, 'cron', hour=9, minute=0)
    scheduler.start()


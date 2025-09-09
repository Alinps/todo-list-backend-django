# apps.py
from django.apps import AppConfig
import threading


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'  # ✅ Make sure this matches your app folder name

    def ready(self):
        """
        Runs when Django starts.
        - Loads signals
        - Starts scheduler
        - Starts background thread for due task checking
        """
        # Load signals
        import api.signals

        # Start scheduler (if you are using APScheduler or similar)
        from . import scheduler
        scheduler.start()

        # Start background thread for checking due tasks
        from .tasks import check_due_tasks
        threading.Thread(target=check_due_tasks, daemon=True).start()

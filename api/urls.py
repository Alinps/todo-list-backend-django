from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, register_user, login_user, admin_users, admin_stats, log_event,tasks_due_tomorrow

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='tasks')

urlpatterns = [
    path('register/', register_user),
    path('login/', login_user),
    path('log-event/', log_event),

    # Admin APIs
    path('admin/users/', admin_users),
    path('admin/stats/', admin_stats),
    path('tasks/due-tomorrow/',tasks_due_tomorrow, name='tasks_due_tomorrow'),

    path('', include(router.urls)),
]

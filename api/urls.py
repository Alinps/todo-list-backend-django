from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, register_user, login_user, admin_users, admin_stats, log_event,tasks_due_tomorrow,get_notifications,mark_as_read,ProfileViewSet

router = DefaultRouter()
# router.register('tasks', TaskViewSet, basename='tasks')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', register_user),
    path('login/', login_user),
    path('log-event/', log_event),

    # Admin APIs
    path('admin/users/', admin_users),
    path('admin/stats/', admin_stats),
    path('tasks/due-tomorrow/',tasks_due_tomorrow, name='tasks_due_tomorrow'),
    path("notifications/",get_notifications),
    path("notifications/<int:notification_id>/read/", mark_as_read),

    path('', include(router.urls)),
]

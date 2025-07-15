from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, register_user, login_user

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='tasks')

urlpatterns = [
    path('register/', register_user),
    path('login/', login_user),
    path('', include(router.urls)),
]

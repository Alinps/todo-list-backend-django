from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Q
from datetime import datetime

from .models import Task, AuditLog
from .serializers import TaskSerializer, UserSerializer, AdminUserSerializer


# @api_view(['POST'])
# @permission_classes([AllowAny])
# def register_user(request):
#     username = request.data.get('username')
#     password = request.data.get('password')
#     email = request.data.get('email')
    

#     if not username or not password:
#         return Response({'error': 'Username and password required'}, status=400)

#     if User.objects.filter(username=username).exists():
#         return Response({'error': 'User already exists'}, status=400)

#     user = User.objects.create_user(username=username, password=password, email=email)
#     token = Token.objects.create(user=user)
#     return Response({
#         'token': token.key,
#         'user_id': user.id,
#         'username': user.username,
#         'is_staff': user.is_staff,
#         'is_superuser': user.is_superuser,
#     })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from .models import UserProfile  # import your Profile model

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from .models import UserProfile

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')

    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'User already exists'}, status=400)

    # Create the user
    user = User.objects.create_user(username=username, password=password, email=email)
    
    # Create or update profile safely
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.phone_number = phone_number
    profile.save()

    # Create auth token
    token = Token.objects.create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'phone_number': profile.phone_number,
    }, status=201)



@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)

    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })
    return Response({'error': 'Invalid Credentials'}, status=400)


# class TaskViewSet(viewsets.ModelViewSet):
#     serializer_class = TaskSerializer
#     permission_classes = [IsAuthenticated]  

#     def get_queryset(self):
#         user = self.request.user
#         tasks = Task.objects.filter(user=user).order_by('-due_date')

#         status_param = self.request.query_params.get('status')
#         search = self.request.query_params.get('search')

#         if status_param == 'pending':
#             tasks = tasks.filter(is_completed=False)
#         elif status_param == 'completed':
#             tasks = tasks.filter(is_completed=True)

#         if search:
#             tasks = tasks.filter(title__icontains=search)

#         return tasks

#     def perform_create(self, serializer):
#         task = serializer.save(user=self.request.user)
#         AuditLog.objects.create(user=self.request.user, action='create', task=task)

#     def perform_update(self, serializer):
#         instance = self.get_object()
#         was_completed = instance.is_completed
#         task = serializer.save()
#         # If completion state changed, record precise action; otherwise generic update
#         now_completed = task.is_completed
#         if was_completed != now_completed:
#             AuditLog.objects.create(
#                 user=self.request.user,
#                 action='complete_true' if now_completed else 'complete_false',
#                 task=task
#             )
#         else:
#             AuditLog.objects.create(user=self.request.user, action='update', task=task)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         # Log before delete so FK can still reference the task
#         AuditLog.objects.create(user=request.user, action='delete', task=instance)
#         return super().destroy(request, *args, **kwargs)




from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Task, AuditLog, UserProfile
from .serializers import TaskSerializer
from rest_framework.exceptions import PermissionDenied

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]  

    def get_queryset(self):
        user = self.request.user
        tasks = Task.objects.filter(user=user).order_by('-due_date')

        # --- Filtering by status ---
        status_param = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if status_param == 'pending':
            tasks = tasks.filter(is_completed=False)
        elif status_param == 'completed':
            tasks = tasks.filter(is_completed=True)

        # --- Search by title ---
        if search:
            tasks = tasks.filter(title__icontains=search)

        return tasks

    # ---------- Task Create with Premium Check ----------
    def perform_create(self, serializer):
        user = self.request.user
        profile = user.profile  # Profile auto-created via signals

        # Count the user's tasks
        task_count = Task.objects.filter(user=user).count()

        # Restrict non-premium users to 5 tasks
        if not profile.is_premium and task_count >= 5:
           raise PermissionDenied("Free plan limit reached. Upgrade to premium.")
        # Save task and log
        task = serializer.save(user=user)
        AuditLog.objects.create(user=user, action='create', task=task)

    # ---------- Task Update ----------
    def perform_update(self, serializer):
        instance = self.get_object()
        was_completed = instance.is_completed
        task = serializer.save()

        now_completed = task.is_completed
        if was_completed != now_completed:
            # Log if completion state changed
            AuditLog.objects.create(
                user=self.request.user,
                action='complete_true' if now_completed else 'complete_false',
                task=task
            )
        else:
            AuditLog.objects.create(user=self.request.user, action='update', task=task)

    # ---------- Task Delete ----------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Log before delete so FK can still reference the task
        AuditLog.objects.create(user=request.user, action='delete', task=instance)
        return super().destroy(request, *args, **kwargs)
    
# views.py
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def upgrade_premium(self, request):
        profile = request.user.profile
        profile.is_premium = True
        profile.save()
        return Response({"message": "You are now a premium user!"})





# ----- Simple endpoint to log client-side-only events (import/export) -----
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_event(request):
    action = request.data.get('action')
    meta = request.data.get('meta', {}) or {}
    if action not in ['import', 'export']:
        return Response({'error': 'Unsupported action'}, status=400)
    AuditLog.objects.create(user=request.user, action=action, meta=meta)
    return Response({'status': 'ok'})


# ----- Admin endpoints -----
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_users(request):
    qs = User.objects.all().order_by('-date_joined')

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    search = request.query_params.get('search')

    if date_from:
        qs = qs.filter(date_joined__date__gte=date_from)
    if date_to:
        qs = qs.filter(date_joined__date__lte=date_to)
    if search:
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))

    data = AdminUserSerializer(qs, many=True).data
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_stats(request):
    """
    Optional query params: date_from, date_to, user_id
    """
    logs = AuditLog.objects.all()

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    user_id = request.query_params.get('user_id')

    if user_id:
        logs = logs.filter(user_id=user_id)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    def count(action):
        return logs.filter(action=action).count()

    data = {
        'tasks_created': count('create'),
        'tasks_deleted': count('delete'),
        'tasks_completed': count('complete_true'),
        'tasks_uncompleted': count('complete_false'),
        'tasks_updated': count('update'),
        'imports': count('import'),
        'exports': count('export'),
    }
    return Response(data)



# views.py dedktop notification
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import date, timedelta
from .models import Task
from .serializers import TaskSerializer

# @api_view(['GET'])
# @permission_classes([AllowAny])
# def tasks_due_tomorrow(request):
#     tomorrow = date.today() + timedelta(days=1)
#     tasks = Task.objects.filter(due_date=tomorrow, is_completed=False)
#     serializer = TaskSerializer(tasks, many=True)
#     return Response(serializer.data)


from datetime import date, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # switch to IsAuthenticated
def tasks_due_tomorrow(request):
    tomorrow = date.today() + timedelta(days=1)
    tasks = Task.objects.filter(
        due_date=tomorrow,
        is_completed=False,
        user=request.user  # only fetch tasks of the logged-in user
    )
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)






#view for notification scheduler endpoint
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    data = [{"id": n.id, "message": n.message, "created_at": n.created_at} for n in notifications]
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    try:
        notif = Notification.objects.get(id=notification_id, user=request.user)
        notif.is_read = True
        notif.save()
        return Response({"status": "ok"})
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

 
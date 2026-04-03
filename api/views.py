import logging
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Q
from .serializers import (
    TaskSerializer,
    AdminUserSerializer,
    ProfileDetailSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
)
from .models import Task, AuditLog, UserProfile
from rest_framework.exceptions import PermissionDenied
from datetime import date, timedelta
from .models import Notification
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)


def _user_label(request):
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"{user.username}({user.id})"
    return "anonymous"



@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    confirm_password = request.data.get('confirm_password')
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')
    logger.info("endpoint.register_user start username=%s email=%s", username, email)

    # Basic validation
    if not username or not password or not confirm_password or not email:
        logger.warning("endpoint.register_user validation_failed reason=missing_required_fields")
        return Response(
            {'error': 'Username, email, password and confirm password are required'},
            status=400
        )

    # Password match check
    if password != confirm_password:
        logger.warning("endpoint.register_user validation_failed reason=password_mismatch username=%s", username)
        return Response({'error': 'Passwords do not match'}, status=400)

    # Email format validation
    try:
        validate_email(email)
    except ValidationError:
        logger.warning("endpoint.register_user validation_failed reason=invalid_email username=%s", username)
        return Response({'error': 'Invalid email format'}, status=400)

    # Check email uniqueness (recommended)
    if User.objects.filter(email=email).exists():
        logger.warning("endpoint.register_user validation_failed reason=email_exists email=%s", email)
        return Response({'error': 'Email already exists'}, status=400)

    # Django password validation
    try:
        validate_password(password)
    except ValidationError as e:
        logger.warning("endpoint.register_user validation_failed reason=weak_password username=%s", username)
        return Response({'error': e.messages}, status=400)

    # Check if username exists
    if User.objects.filter(username=username).exists():
        logger.warning("endpoint.register_user validation_failed reason=username_exists username=%s", username)
        return Response({'error': 'User already exists'}, status=400)

    # Create the user
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    
    # Profile handling
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.phone_number = phone_number
    profile.save()

    # Token creation
    token = Token.objects.create(user=user)
    logger.info("endpoint.register_user success user=%s token_created=%s", user.username, bool(token))

    return Response({"message": "User created Successfully"}, status=201)



@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    logger.info("endpoint.login_user start username=%s", username)
    user = authenticate(username=username, password=password)

    if user:
        token, _ = Token.objects.get_or_create(user=user)
        logger.info("endpoint.login_user success user=%s", user.username)
        return Response({
            'token': token.key,
            'user_id': user.id, # type: ignore
            'username': user.username,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })
    logger.warning("endpoint.login_user failed username=%s", username)
    return Response({'error': 'Invalid Credentials'}, status=400)








class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]  

    def get_queryset(self):
        user = self.request.user
        tasks = Task.objects.filter(user=user).order_by('-due_date', '-due_time')

        # --- Filtering by status ---
        status_param = self.request.query_params.get('status') # type: ignore
        search = self.request.query_params.get('search') # type: ignore

        if status_param == 'pending':
            tasks = tasks.filter(is_completed=False)
        elif status_param == 'completed':
            tasks = tasks.filter(is_completed=True)

        # --- Search by title ---
        if search:
            tasks = tasks.filter(title__icontains=search)

        return tasks

    def list(self, request, *args, **kwargs):
        logger.info("endpoint.tasks.list user=%s", _user_label(request))
        response = super().list(request, *args, **kwargs)
        logger.info("endpoint.tasks.list end user=%s status=%s", _user_label(request), response.status_code)
        return response

    def retrieve(self, request, *args, **kwargs):
        logger.info("endpoint.tasks.retrieve user=%s task_id=%s", _user_label(request), kwargs.get("pk"))
        response = super().retrieve(request, *args, **kwargs)
        logger.info(
            "endpoint.tasks.retrieve end user=%s task_id=%s status=%s",
            _user_label(request),
            kwargs.get("pk"),
            response.status_code,
        )
        return response

    def create(self, request, *args, **kwargs):
        logger.info("endpoint.tasks.create start user=%s", _user_label(request))
        response = super().create(request, *args, **kwargs)
        logger.info("endpoint.tasks.create end user=%s status=%s", _user_label(request), response.status_code)
        return response

    def update(self, request, *args, **kwargs):
        logger.info("endpoint.tasks.update start user=%s task_id=%s", _user_label(request), kwargs.get("pk"))
        response = super().update(request, *args, **kwargs)
        logger.info(
            "endpoint.tasks.update end user=%s task_id=%s status=%s",
            _user_label(request),
            kwargs.get("pk"),
            response.status_code,
        )
        return response

    def partial_update(self, request, *args, **kwargs):
        logger.info("endpoint.tasks.partial_update start user=%s task_id=%s", _user_label(request), kwargs.get("pk"))
        response = super().partial_update(request, *args, **kwargs)
        logger.info(
            "endpoint.tasks.partial_update end user=%s task_id=%s status=%s",
            _user_label(request),
            kwargs.get("pk"),
            response.status_code,
        )
        return response
    



    # ---------- Task Create with Premium Check ----------
    def perform_create(self, serializer):
        user = self.request.user
        profile = user.profile  # type: ignore # Profile auto-created via signals

        # Count the user's tasks
        task_count = Task.objects.filter(user=user).count()

        # Restrict non-premium users to 5 tasks
        if not profile.is_premium and task_count >= 5:
            logger.warning("endpoint.tasks.create denied user=%s reason=free_plan_limit", user.username)
            raise PermissionDenied("Free plan limit reached. Upgrade to premium.")
        # Save task and log
        task = serializer.save(user=user)
        AuditLog.objects.create(user=user, action='create', task=task)
        logger.info("endpoint.tasks.create success user=%s task_id=%s", user.username, task.id)

    # ---------- Task Update ----------
    def perform_update(self, serializer):
        instance = self.get_object()
        was_completed = instance.is_completed
        old_due_date = instance.due_date
        old_due_time = instance.due_time
        task = serializer.save()

        # If schedule changed, allow reminder pipeline to send for the new schedule.
        if old_due_date != task.due_date or old_due_time != task.due_time:
            task.notified = False
            task.save(update_fields=["notified"])

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
        logger.info("endpoint.tasks.update success user=%s task_id=%s", self.request.user.username, task.id)

    # ---------- Task Delete ----------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info("endpoint.tasks.delete start user=%s task_id=%s", _user_label(request), instance.id)
        # Log before delete so FK can still reference the task
        AuditLog.objects.create(user=request.user, action='delete', task=instance)
        response = super().destroy(request, *args, **kwargs)
        logger.info("endpoint.tasks.delete end user=%s task_id=%s status=%s", _user_label(request), instance.id, response.status_code)
        return response
    
# views.py
class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def me(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        data = ProfileDetailSerializer(request.user).data
        logger.info("endpoint.profile.me success user=%s", _user_label(request))
        return Response(data)

    @action(detail=False, methods=["patch"], url_path="update")
    def update_profile(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user = request.user
        user_fields = []
        if "username" in validated:
            user.username = validated["username"]
            user_fields.append("username")
        if "email" in validated:
            user.email = validated["email"]
            user_fields.append("email")
        if user_fields:
            user.save(update_fields=user_fields)

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if "phone_number" in validated:
            profile.phone_number = validated["phone_number"]
            profile.save(update_fields=["phone_number"])

        logger.info("endpoint.profile.update success user=%s fields=%s", _user_label(request), ",".join(validated.keys()))
        return Response(ProfileDetailSerializer(user).data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Rotate token so old token cannot be reused.
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        logger.info("endpoint.profile.change_password success user=%s", _user_label(request))
        return Response(
            {
                "message": "Password changed successfully.",
                "token": new_token.key,
            }
        )

    @action(detail=False, methods=["post"])
    def upgrade_premium(self, request):
        profile = request.user.profile
        profile.is_premium = True
        profile.save()
        logger.info("endpoint.profile.upgrade_premium success user=%s", _user_label(request))
        return Response({"message": "You are now a premium user!"})





# ----- Simple endpoint to log client-side-only events (import/export) -----
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_event(request):
    action = request.data.get('action')
    meta = request.data.get('meta', {}) or {}
    if action not in ['import', 'export']:
        logger.warning("endpoint.log_event failed user=%s action=%s", _user_label(request), action)
        return Response({'error': 'Unsupported action'}, status=400)
    AuditLog.objects.create(user=request.user, action=action, meta=meta)
    logger.info("endpoint.log_event success user=%s action=%s", _user_label(request), action)
    return Response({'status': 'ok'})




# ----- Admin endpoints -----
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_users(request):
    logger.info("endpoint.admin_users start user=%s", _user_label(request))
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
    logger.info("endpoint.admin_users success user=%s count=%s", _user_label(request), len(data))
    return Response(data)





@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_stats(request):
    """
    Optional query params: date_from, date_to, user_id
    """
    logger.info("endpoint.admin_stats start user=%s", _user_label(request))
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
    logger.info("endpoint.admin_stats success user=%s", _user_label(request))
    return Response(data)







@api_view(['GET'])
@permission_classes([IsAuthenticated])  # switch to IsAuthenticated
def tasks_due_tomorrow(request):
    logger.info("endpoint.tasks_due_tomorrow start user=%s", _user_label(request))
    tomorrow = date.today() + timedelta(days=1)
    tasks = Task.objects.filter(
        due_date=tomorrow,
        is_completed=False,
        user=request.user  # only fetch tasks of the logged-in user
    ).order_by("due_time")
    serializer = TaskSerializer(tasks, many=True)
    logger.info("endpoint.tasks_due_tomorrow success user=%s count=%s", _user_label(request), len(serializer.data))
    return Response(serializer.data)






#view for notification scheduler endpoint
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    logger.info("endpoint.get_notifications start user=%s", _user_label(request))
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    data = [{"id": n.id, "message": n.message, "created_at": n.created_at} for n in notifications] # type: ignore
    logger.info("endpoint.get_notifications success user=%s count=%s", _user_label(request), len(data))
    return Response(data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    try:
        logger.info("endpoint.mark_as_read start user=%s notification_id=%s", _user_label(request), notification_id)
        notif = Notification.objects.get(id=notification_id, user=request.user)
        notif.is_read = True
        notif.save()
        logger.info("endpoint.mark_as_read success user=%s notification_id=%s", _user_label(request), notification_id)
        return Response({"status": "ok"})
    except Notification.DoesNotExist:
        logger.warning("endpoint.mark_as_read failed user=%s notification_id=%s reason=not_found", _user_label(request), notification_id)
        return Response({"error": "Not found"}, status=404)

 

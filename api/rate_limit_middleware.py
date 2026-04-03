import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _path_is_limited(path):
        prefixes = getattr(settings, "RATE_LIMIT_PATH_PREFIXES", ["/api/"])
        return any(path.startswith(prefix) for prefix in prefixes)

    @staticmethod
    def _is_exempt(path):
        exempt_paths = getattr(settings, "RATE_LIMIT_EXEMPT_PATHS", [])
        return path in exempt_paths

    def __call__(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return self.get_response(request)

        if request.method == "OPTIONS":
            return self.get_response(request)

        path = request.path
        if not self._path_is_limited(path) or self._is_exempt(path):
            return self.get_response(request)

        window_seconds = int(getattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60))
        max_requests = int(getattr(settings, "RATE_LIMIT_MAX_REQUESTS", 120))
        now = int(time.time())
        window = now // window_seconds

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            identity = f"user:{user.id}"
        else:
            identity = f"ip:{self._client_ip(request)}"

        cache_key = f"rl:{identity}:{window}"

        current = cache.get(cache_key)
        if current is None:
            cache.add(cache_key, 1, timeout=window_seconds)
            current = 1
        else:
            try:
                current = cache.incr(cache_key)
            except ValueError:
                cache.add(cache_key, 1, timeout=window_seconds)
                current = 1

        if current > max_requests:
            retry_after = window_seconds - (now % window_seconds)
            logger.warning(
                "rate_limit.blocked identity=%s path=%s method=%s current=%s limit=%s retry_after=%s",
                identity,
                path,
                request.method,
                current,
                max_requests,
                retry_after,
            )
            response = JsonResponse(
                {
                    "error": "rate_limit_exceeded",
                    "detail": "Too many requests. Please try again later.",
                },
                status=429,
            )
            response["Retry-After"] = str(retry_after)
            return response

        return self.get_response(request)

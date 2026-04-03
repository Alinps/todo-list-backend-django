import logging
import time


logger = logging.getLogger(__name__)


class RequestResponseLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _user_label(request):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return f"{user.username}({user.id})"
        return "anonymous"

    def __call__(self, request):
        start = time.perf_counter()
        method = request.method
        path = request.get_full_path()
        ip = self._client_ip(request)
        user = self._user_label(request)

        logger.info(
            "request.start method=%s path=%s user=%s ip=%s",
            method,
            path,
            user,
            ip,
        )

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request.error method=%s path=%s user=%s ip=%s duration_ms=%.2f",
                method,
                path,
                user,
                ip,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request.end method=%s path=%s user=%s ip=%s status=%s duration_ms=%.2f",
            method,
            path,
            user,
            ip,
            response.status_code,
            duration_ms,
        )
        return response

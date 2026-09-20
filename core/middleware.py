import json
import logging
import time
import uuid

from django.http import JsonResponse


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/live":
            from django.conf import settings

            version = getattr(settings, "APP_VERSION", "dev")
            return JsonResponse({"status": "ok", "version": version})

        if request.path == "/health/ready":
            from django.db import connection

            try:
                connection.ensure_connection()
                return JsonResponse({"status": "ready"})
            except Exception:
                return JsonResponse({"status": "unavailable"}, status=503)

        return self.get_response(request)


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class AccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("access")

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = round((time.time() - start) * 1000, 2)

        self.logger.info(
            json.dumps(
                {
                    "request_id": getattr(request, "request_id", ""),
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration,
                    "user_id": getattr(request.user, "id", None) if hasattr(request, "user") else None,
                }
            )
        )
        return response

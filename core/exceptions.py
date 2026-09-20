import uuid

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, APIException):
            response_status = exc.status_code
        else:
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response_data = {
                "error": {
                    "code": "internal_error",
                    "message": "Erro inesperado.",
                    "request_id": context.get("request", None)
                    and getattr(context["request"], "request_id", str(uuid.uuid4())),
                }
            }
            from rest_framework.response import Response

            return Response(response_data, status=response_status)
        return response

    request_id = context.get("request", None) and getattr(
        context["request"], "request_id", str(uuid.uuid4())
    )

    if isinstance(response.data, dict):
        error_code = "validation_error"
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "not_authenticated"
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "permission_denied"
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "not_found"
        elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            error_code = "method_not_allowed"
        elif response.status_code == status.HTTP_409_CONFLICT:
            error_code = "conflict"
        elif response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            error_code = "unsupported_media_type"
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "throttled"

        detail = response.data.get("detail", response.data)
        response.data = {
            "error": {
                "code": error_code,
                "message": str(detail) if isinstance(detail, str) else "Dados inválidos.",
                "details": detail if not isinstance(detail, str) else None,
                "request_id": request_id,
            }
        }

    return response

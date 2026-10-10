"""
Custom exception handler for consistent API error responses.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to ensure every error response
    follows a consistent JSON structure:

    {
        "error": {
            "code": "error_code",
            "message": "Human-readable message",
            "details": { ... }  // optional
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": {
                "code": _get_error_code(response.status_code),
                "message": _get_error_message(response),
                "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
            }
        }
        response.data = error_data
    else:
        # Unhandled exceptions — log and return 500
        logger.exception(
            "Unhandled exception in %s",
            context.get("view", "unknown"),
            exc_info=exc,
        )
        error_data = {
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        }
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


def _get_error_code(status_code: int) -> str:
    """Map HTTP status codes to machine-readable error codes."""
    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        429: "too_many_requests",
        500: "internal_server_error",
    }
    return code_map.get(status_code, f"error_{status_code}")


def _get_error_message(response) -> str:
    """Extract a human-readable message from a DRF response."""
    data = response.data
    if isinstance(data, dict):
        detail = data.get("detail")
        if detail:
            return str(detail)
        # Return the first error message found
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            elif isinstance(value, str):
                return f"{key}: {value}"
    elif isinstance(data, list) and data:
        return str(data[0])
    return "An error occurred."

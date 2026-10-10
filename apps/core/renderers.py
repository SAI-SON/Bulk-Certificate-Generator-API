"""
Custom renderers for consistent API responses.
"""
from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """
    Wraps successful responses in a standard envelope:
    {
        "status": "success",
        "data": { ... }
    }
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        # Don't wrap error responses (handled by custom_exception_handler)
        if response and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        # Don't wrap if data is already wrapped
        if isinstance(data, dict) and "status" in data:
            return super().render(data, accepted_media_type, renderer_context)

        wrapped = {
            "status": "success",
            "data": data,
        }
        return super().render(wrapped, accepted_media_type, renderer_context)

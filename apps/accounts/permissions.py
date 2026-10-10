from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    Assumes the model instance has an `owner` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Permissions are only granted if obj.owner matches request.user
        return hasattr(obj, "owner") and obj.owner == request.user

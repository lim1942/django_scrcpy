from rest_framework.permissions import BasePermission


class TaskPermission(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.method == 'GET':
            return True
        return False

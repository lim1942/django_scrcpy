from rest_framework.permissions import BasePermission


class GeneralPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    # def has_object_permission(self, request, view, obj):
    #     if request.method == 'GET':
    #         return True
    #     return False

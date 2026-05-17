from rest_framework import permissions

class IsModerator(permissions.BasePermission):
    """Права модератора (пользователь с is_staff=True)"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsModeratorOrReadOnly(permissions.BasePermission):
    """Модератор может всё, остальные только чтение"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwner(permissions.BasePermission):
    """Только владелец объекта"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if hasattr(obj, 'creator'):
            return obj.creator == request.user
        if hasattr(obj, 'account_request') and hasattr(obj.account_request, 'creator'):
            return obj.account_request.creator == request.user
        return False
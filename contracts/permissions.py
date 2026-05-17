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


class IsCreatorOrModerator(permissions.BasePermission):
    """Создатель или модератор могут редактировать"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Модератор может всё
        if request.user and request.user.is_staff:
            return True
        # Создатель может редактировать свою заявку
        return hasattr(obj, 'creator') and obj.creator == request.user


class IsOwner(permissions.BasePermission):
    """Только владелец объекта"""
    
    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user
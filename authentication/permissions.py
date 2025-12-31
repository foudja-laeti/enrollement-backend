# authentication/permissions.py
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Permission pour super administrateur uniquement"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'super_admin'


class IsAdminAcademique(BasePermission):
    """Permission pour administrateur académique ou supérieur"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['super_admin', 'admin_academique']
        )


class IsResponsableFiliere(BasePermission):
    """Permission pour responsable de filière ou supérieur"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['super_admin', 'admin_academique', 'responsable_filiere']
        )


class IsAdminOrOwner(BasePermission):
    """Permission pour admin ou propriétaire de la ressource"""
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['super_admin', 'admin_academique']:
            return True
        return obj == request.user or (hasattr(obj, 'user') and obj.user == request.user)
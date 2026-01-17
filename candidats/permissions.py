# candidats/permissions.py
from rest_framework import permissions

class IsResponsableFiliere(permissions.BasePermission):
    """
    Permission pour vérifier que l'utilisateur est un responsable de filière
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'responsable_filiere' and
            hasattr(request.user, 'responsable_filiere_profile')
        )
    

class IsAdminAcademique(permissions.BasePermission):
    """Permission pour administrateur académique ou supérieur"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['super_admin', 'admin_academique']
        )
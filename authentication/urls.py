# authentication/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentification publique
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-quitus/', views.verify_quitus_view, name='verify_quitus'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profil
    path('profile/', views.profile_view, name='profile'),
    
    # Gestion des utilisateurs (ADMIN)
    path('users/', views.list_users_view, name='list_users'),
    path('users/create/', views.create_admin_user_view, name='create_admin_user'),
    path('users/<int:user_id>/', views.get_user_view, name='get_user'),
    path('users/<int:user_id>/update/', views.update_user_view, name='update_user'),
    path('users/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password_view, name='reset_user_password'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
    
    # Statistiques et logs
    path('statistics/', views.get_statistics_view, name='get_statistics'),
    path('action-logs/', views.get_action_logs_view, name='get_action_logs'),
]
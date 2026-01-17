# authentication/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from . import views
router = DefaultRouter()


urlpatterns = [
    # ========================================
    # AUTHENTIFICATION PUBLIQUE
    # ========================================
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-quitus/', views.verify_quitus_view, name='verify_quitus'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ========================================
    # PROFIL
    # ========================================
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change-password'),
    # ========================================
    # GESTION UTILISATEURS (ADMIN)
    # ========================================
    
    # Liste et création
    path('users/', views.list_users_view, name='list_users'),
    path('users/create/', views.create_admin_user_view, name='create_admin_user'),  # ✅ ENDPOINT UNIFIÉ
    
    # Actions spécifiques (ORDRE IMPORTANT : spécifique avant générique)
    path('users/delete/<int:pk>/', views.delete_user_view, name='delete_user'),
    path('users/<int:pk>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),
    path('users/<int:pk>/reset-password/', views.reset_user_password_view, name='reset_user_password'),
    path('users/<int:user_id>/detail/', views.get_user_view, name='get_user'),
    
    # Modification générique (DOIT ÊTRE EN DERNIER)
    path('users/<int:pk>/', views.update_user_view, name='update_user'),
    
    # ========================================
    # STATISTIQUES & LOGS
    # ========================================
    path('statistics/', views.get_statistics_view, name='get_statistics'),
    path('action-logs/', views.get_action_logs_view, name='get_action_logs'),
    path('evolution-candidats/', views.get_evolution_candidats_view, name='evolution_candidats'),
    
    # ========================================
    # RÉFÉRENCES (Filières, etc.)
    # ========================================
    path('filieres/', views.list_filieres_view, name='list_filieres'),
     # ========================================
    # PROFIL & MOT DE PASSE
    # ========================================
    path('profile/', views.profile_view, name='profile'),  # GET, PATCH, PUT
    path('change-password/', views.change_password_view, name='change_password'),  # POST
    path('update-profile/', views.update_profile_view, name='update_profile'),  # POST
    
]

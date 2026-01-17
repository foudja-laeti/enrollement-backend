from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour ResponsableFiliereViewSet UNIQUEMENT
router = DefaultRouter()
router.register(r'respfiliere', views.ResponsableFiliereViewSet, basename='respfiliere')
router.register(r'admin-academique', views.AdminAcademiqueViewSet, basename='admin-acad')

urlpatterns = [
    # ========================================
    # ENRÔLEMENT CANDIDAT
    # ========================================
    path('enrollement/', views.enrollement_view, name='enrollement'),
    path('mon-profil/', views.mon_profil_view, name='mon-profil'),
    path('mon-dossier/', views.mon_dossier_view, name='mon-dossier'),
    path('check-enrollment/', views.check_enrollment_status, name='check-enrollment'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-read'),
    path('notifications/<int:notification_id>/', views.delete_notification, name='delete-notification'),
    path('notifications/welcome/', views.create_welcome_notification, name='welcome-notification'),

    # ========================================
    # GESTION DOCUMENTS (si tu as ces vues)
    # ========================================
    # path('documents/upload/', views.upload_document_view, name='upload_document'),
    # path('documents/<int:doc_id>/delete/', views.delete_document_view, name='delete_document'),
    
    # ========================================
    # RESPONSABLE FILIÈRE (ViewSet avec Router)
    # ========================================
    path('', include(router.urls)),
    # Cela génère automatiquement:
    # GET  /api/candidats/respfiliere/dashboard-stats/
    # GET  /api/candidats/respfiliere/mes-candidats/
    # GET  /api/candidats/respfiliere/<id>/candidat-detail/
    # POST /api/candidats/respfiliere/<id>/valider-dossier/
    # POST /api/candidats/respfiliere/<id>/rejeter-dossier/
    # GET  /api/candidats/respfiliere/profil-filiere/
    # GET  /api/candidats/respfiliere/export-stats/
]
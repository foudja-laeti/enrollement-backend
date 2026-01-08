# candidats/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour le ViewSet
router = DefaultRouter()
router.register(r'respfiliere', views.ResponsableFiliereViewSet, basename='respfiliere')

urlpatterns = [
    # Route existante pour l'enrôlement
    path('enrollement/', views.enrollement_view, name='enrollement'),
    
    # Routes du ResponsableFiliereViewSet
    path('', include(router.urls)),
]

# Les endpoints disponibles seront:
# POST /api/candidats/enrollement/
# GET  /api/candidats/respfiliere/dashboard_stats/
# GET  /api/candidats/respfiliere/mes_candidats/
# GET  /api/candidats/respfiliere/{id}/candidat_detail/

# POST /api/candidats/respfiliere/{id}/rejeter_dossier/
# GET  /api/candidats/respfiliere/profil_filiere/
from django.urls import path
from . import views

urlpatterns = [
    # Listes simples
    path("filieres/", views.FiliereListView.as_view(), name="filieres"),
    path("niveaux/", views.NiveauListView.as_view(), name="niveaux"),
    path("diplomes/", views.DiplomeListView.as_view(), name="diplomes"),
    path("centres-examen/", views.CentreExamenListView.as_view(), name="centres_examen"),
    path("centres-depot/", views.CentreDepotListView.as_view(), name="centres_depot"),
    
    # ✅ RÉGIONS/DEPARTEMENTS (SANS "config/")
    path("regions/", views.RegionListView.as_view(), name="regions"),              # ✅ CORRIGÉ
    path("departements/", views.DepartementListView.as_view(), name="departements"), # ✅ CORRIGÉ

    # BAC/SERIE (nouveau)
    path("bacs/", views.BacListView.as_view(), name="bacs"),
    path("series/", views.SerieListView.as_view(), name="series"),
    path("mentions/", views.MentionListView.as_view(), name="mentions"),
    
    # CASCADE (tes endpoints avancés)
    path('bacs/<int:bac_id>/mentions/', views.mentions_by_bac, name='mentions-by-bac'),
    path("bacs/<int:bac_id>/series/", views.series_by_bac, name="series_by_bac"),
    path("series/<int:serie_id>/filieres/", views.filieres_by_serie, name="filieres_by_serie"),
    path("series/<int:serie_id>/filieres/<int:filiere_id>/niveaux/", views.niveaux_by_serie_filiere, name="niveaux_by_serie_filiere"),
    path("filieres/<int:filiere_id>/niveaux/<int:niveau_id>/diplomes/", views.diplomes_by_niveau_filiere, name="diplomes_by_niveau_filiere"),
]

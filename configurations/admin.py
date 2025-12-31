from django.contrib import admin
from .models import (
    AnneeScolaire, Niveau, Filiere, FiliereNiveau, 
    Diplome, FiliereDiplome, CentreExamen, CentreDepot,
    Bac, Serie, Mention, SerieFiliere  # ✅ AJOUTE CES IMPORTS
)


@admin.register(AnneeScolaire)
class AnneeScolaireAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'date_debut', 'date_fin', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['libelle']
    ordering = ['-date_debut']


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'ordre']
    ordering = ['ordre']


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'duree_annees', 'frais_inscription', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'libelle']


@admin.register(FiliereNiveau)
class FiliereNiveauAdmin(admin.ModelAdmin):
    list_display = ['filiere', 'niveau', 'places_disponibles', 'places_occupees', 'frais_scolarite']
    list_filter = ['filiere', 'niveau']


@admin.register(Diplome)
class DiplomeAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'niveau_etude']
    search_fields = ['code', 'libelle']


@admin.register(FiliereDiplome)
class FiliereDiplomeAdmin(admin.ModelAdmin):
    list_display = ['filiere', 'niveau', 'diplome', 'is_required']
    list_filter = ['filiere', 'niveau', 'is_required']


@admin.register(CentreExamen)
class CentreExamenAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'ville', 'capacite', 'is_active']
    list_filter = ['ville', 'is_active']
    search_fields = ['code', 'nom', 'ville']


@admin.register(CentreDepot)
class CentreDepotAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'ville', 'is_active']
    list_filter = ['ville', 'is_active']
    search_fields = ['code', 'nom', 'ville']


# ========================================
# ✅ NOUVEAUX ADMINS POUR BAC/SERIE/MENTION
# ========================================

@admin.register(Bac)
class BacAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'libelle', 'created_at']
    search_fields = ['code', 'libelle']
    ordering = ['code']


@admin.register(Serie)
class SerieAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'libelle', 'bac', 'created_at']
    list_filter = ['bac']
    search_fields = ['code', 'libelle']
    ordering = ['bac', 'code']


@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'libelle', 'minimum_points', 'maximum_points', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'libelle']
    ordering = ['minimum_points']


@admin.register(SerieFiliere)
class SerieFiliereAdmin(admin.ModelAdmin):
    list_display = ['id', 'serie', 'filiere', 'niveau', 'created_at']
    list_filter = ['serie', 'filiere', 'niveau']
    search_fields = ['serie__code', 'filiere__code', 'niveau__code']
    ordering = ['serie', 'filiere', 'niveau']
    
    # ✅ Affichage personnalisé pour les foreign keys
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('serie', 'filiere', 'niveau')
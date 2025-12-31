from django.contrib import admin
from .models import Candidat, Quitus, Dossier, Document, Region, Departement

@admin.register(Quitus)
class QuitusAdmin(admin.ModelAdmin):
    list_display = ['code', 'montant', 'annee_scolaire', 'is_used', 'used_by', 'created_at']
    list_filter = ['is_used', 'annee_scolaire']
    search_fields = ['code']
    readonly_fields = ['used_at', 'created_at', 'updated_at']

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'created_at']
    list_filter = ['created_at']
    search_fields = ['nom', 'code']
    readonly_fields = ['created_at']

@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'region', 'created_at']
    list_filter = ['region']
    search_fields = ['nom', 'code']
    readonly_fields = ['created_at']

@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'nom', 'prenom', 'email', 'sexe', 'region', 'departement', 'statut_dossier']
    
    list_filter = ['sexe', 'statut_dossier', 'region', 'departement']
    search_fields = ['nom', 'prenom', 'matricule', 'email']
    
    fieldsets = (
        ('Identité', {'fields': ('nom', 'prenom', 'email', 'sexe', 'date_naissance', 'lieu_naissance')}),
        ('Domicile', {'fields': ('ville', 'quartier', 'region', 'departement')}),
        ('Contact', {'fields': ('telephone_secondaire',)}),
        ('Académique', {'fields': ('bac_id', 'serie_id', 'filiere_id', 'niveau_id', 'mention_id')}),
        ('Parents', {'fields': ('nom_pere', 'nom_mere', 'telephone_pere', 'telephone_mere', 'profession_pere', 'profession_mere')}),
    )
    
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ['numero_dossier', 'candidat', 'annee_scolaire', 'statut', 'date_ouverture']
    list_filter = ['statut', 'annee_scolaire']
    search_fields = ['numero_dossier', 'candidat__nom', 'candidat__prenom']
    readonly_fields = ['numero_dossier', 'date_ouverture', 'created_at', 'updated_at']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['candidat', 'type_document', 'nom_fichier', 'is_verified', 'created_at']
    list_filter = ['type_document', 'is_verified']
    search_fields = ['candidat__nom', 'candidat__prenom', 'nom_fichier']
    readonly_fields = ['created_at', 'updated_at']

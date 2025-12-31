from django.contrib import admin
from .models import Inscription


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ['numero_inscription', 'candidat', 'filiere', 'niveau', 'statut', 'date_soumission']
    list_filter = ['statut', 'filiere', 'niveau', 'annee_scolaire']
    search_fields = ['numero_inscription', 'candidat__nom', 'candidat__prenom']
    readonly_fields = ['numero_inscription', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('numero_inscription', 'candidat', 'dossier', 'annee_scolaire')
        }),
        ('Formation', {
            'fields': ('filiere', 'niveau', 'centre_examen', 'centre_depot')
        }),
        ('Informations académiques', {
            'fields': ('diplome', 'serie', 'annee_obtention_diplome', 'pays_obtention_diplome', 'etablissement_origine', 'ville_etablissement', 'moyenne_generale', 'mention')
        }),
        ('Statut et validation', {
            'fields': ('statut', 'date_soumission', 'date_validation', 'validated_by', 'motif_rejet')
        }),
        ('Documents générés', {
            'fields': ('qr_code_path', 'fiche_inscription_path')
        }),
    )
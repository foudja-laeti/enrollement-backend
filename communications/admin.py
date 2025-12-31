from django.contrib import admin
from .models import Categorie, Actualite, Notification, AuditLog, Epreuve


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type', 'couleur', 'icone']
    list_filter = ['type']



@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'auteur', 'is_published', 'date_publication', 'vues']
    list_filter = ['is_published', 'categorie']
    search_fields = ['titre', 'contenu']
    prepopulated_fields = {'slug': ('titre',)}
    readonly_fields = ['vues', 'created_at', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'user', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
    search_fields = ['titre', 'message', 'user__email']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'table_name', 'record_id', 'ip_address', 'created_at']
    list_filter = ['action', 'table_name']
    search_fields = ['user__email', 'table_name']
    readonly_fields = ['created_at']

@admin.register(Epreuve)
class EpreuveAdmin(admin.ModelAdmin):
    list_display = ['titre', 'filiere', 'annee', 'taille', 'nombre_telechargements', 'is_published']
    list_filter = ['filiere', 'annee', 'is_published']
    search_fields = ['titre', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    readonly_fields = ['nombre_telechargements', 'created_at', 'updated_at', 'taille']
    
    fieldsets = (
        ('📋 Informations générales', {
            'fields': ('titre', 'slug', 'description')
        }),
        ('🏷️ Classification', {
            'fields': ('filiere', 'annee')  # ✅ UNIQUEMENT
        }),
        ('📎 Fichier PDF', {
            'fields': ('fichier', 'taille')
        }),
        ('🌐 Publication', {
            'fields': ('is_published', 'auteur')
        }),
        ('📊 Statistiques', {
            'fields': ('nombre_telechargements', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

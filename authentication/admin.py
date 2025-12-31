# authentication/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from .models import User, CodeQuitus, TransactionBancaire, ResponsableFiliere, UserActionLog


# ==========================================
# USER ADMIN
# ==========================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email_display', 
        'nom_prenom', 
        'role_badge', 
        'status_badges',
        'created_by_display',
        'created_at'
    ]
    list_filter = ['role', 'is_active', 'is_email_verified', 'created_at']
    search_fields = ['email', 'nom', 'prenom']
    ordering = ['-created_at']
    
    fieldsets = (
        ('🔐 Informations de connexion', {
            'fields': ('email', 'password')
        }),
        ('👤 Informations personnelles', {
            'fields': ('nom', 'prenom', 'role')
        }),
        ('✅ Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified')
        }),
        ('📅 Dates importantes', {
            'fields': ('last_login', 'email_verified_at', 'created_at', 'created_by')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'email_verified_at', 'created_by']
    
    def email_display(self, obj):
        """Email avec icône de vérification"""
        icon = '✓' if obj.is_email_verified else '✗'
        color = '#4caf50' if obj.is_email_verified else '#f44336'
        return format_html(
            '<span style="font-weight: bold;">{}</span> '
            '<span style="color: {}; font-size: 16px;">{}</span>',
            obj.email, color, icon
        )
    email_display.short_description = 'Email'
    
    def nom_prenom(self, obj):
        """Nom et prénom formatés"""
        if obj.nom or obj.prenom:
            return format_html(
                '<span style="font-weight: 500;">{}</span>',
                obj.get_full_name()
            )
        return format_html('<span style="color: #999;">-</span>')
    nom_prenom.short_description = 'Nom complet'
    
    def role_badge(self, obj):
        """Badge coloré selon le rôle"""
        colors = {
            'super_admin': '#9c27b0',
            'admin_academique': '#2196f3',
            'responsable_filiere': '#ff9800',
            'candidat': '#4caf50',
        }
        color = colors.get(obj.role, '#757575')
        role_display = obj.get_role_display_custom()
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{}</span>',
            color, role_display
        )
    role_badge.short_description = 'Rôle'
    
    def status_badges(self, obj):
        """Badges de statut"""
        badges = []
        
        # Badge actif/inactif
        if obj.is_active:
            badges.append(
                '<span style="background: #4caf50; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 10px; margin-right: 4px;">ACTIF</span>'
            )
        else:
            badges.append(
                '<span style="background: #f44336; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 10px; margin-right: 4px;">INACTIF</span>'
            )
        
        # Badge staff
        if obj.is_staff:
            badges.append(
                '<span style="background: #673ab7; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 10px;">STAFF</span>'
            )
        
        return format_html(''.join(badges))
    status_badges.short_description = 'Statuts'
    
    def created_by_display(self, obj):
        """Afficher qui a créé l'utilisateur"""
        if obj.created_by:
            url = f'/admin/authentication/user/{obj.created_by.id}/change/'
            return format_html(
                '<a href="{}" style="color: #2196f3;">{}</a>',
                url, obj.created_by.get_full_name()
            )
        return format_html('<span style="color: #999;">Auto-inscription</span>')
    created_by_display.short_description = 'Créé par'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['email']
        return self.readonly_fields


# ==========================================
# RESPONSABLE FILIERE ADMIN
# ==========================================

@admin.register(ResponsableFiliere)
class ResponsableFiliereAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'filiere_display', 'telephone', 'created_at']
    list_filter = ['filiere', 'created_at']
    search_fields = ['user__email', 'user__nom', 'user__prenom', 'telephone']
    raw_id_fields = ['user', 'filiere']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('👤 Utilisateur', {
            'fields': ('user',)
        }),
        ('📚 Affectation', {
            'fields': ('filiere',)
        }),
        ('📞 Contact', {
            'fields': ('telephone',)
        }),
        ('📅 Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_display(self, obj):
        """Affichage de l'utilisateur"""
        url = f'/admin/authentication/user/{obj.user.id}/change/'
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a><br>'
            '<span style="color: #666; font-size: 11px;">{}</span>',
            url, obj.user.get_full_name(), obj.user.email
        )
    user_display.short_description = 'Utilisateur'
    
    def filiere_display(self, obj):
        """Affichage de la filière"""
        if obj.filiere:
            return format_html(
                '<span style="background: #e3f2fd; color: #1976d2; padding: 4px 10px; '
                'border-radius: 8px; font-weight: 500;">{}</span>',
                obj.filiere.nom
            )
        return format_html('<span style="color: #999;">Non assigné</span>')
    filiere_display.short_description = 'Filière'


# ==========================================
# CODE QUITUS ADMIN
# ==========================================

@admin.register(CodeQuitus)
class CodeQuitusAdmin(admin.ModelAdmin):
    list_display = [
        'code_display', 
        'reference_bancaire', 
        'montant_display', 
        'statut_badge', 
        'utilisateur_link',
        'date_generation', 
        'expiration_info'
    ]
    list_filter = [
        'utilise', 
        'date_generation', 
        'date_expiration',
    ]
    search_fields = ['code', 'reference_bancaire', 'utilisateur__email']
    readonly_fields = ['date_generation', 'date_utilisation', 'stats_display']
    date_hierarchy = 'date_generation'
    
    fieldsets = (
        ('🎫 Informations du Code', {
            'fields': ('code', 'reference_bancaire', 'montant')
        }),
        ('📊 Statut', {
            'fields': ('utilise', 'utilisateur', 'date_utilisation', 'stats_display')
        }),
        ('📅 Dates', {
            'fields': ('date_generation', 'date_expiration')
        }),
    )
    
    actions = ['generer_codes_10', 'generer_codes_50', 'generer_codes_100']
    
    def code_display(self, obj):
        """Affichage stylé du code"""
        return format_html(
            '<span style="font-family: monospace; font-size: 15px; font-weight: bold; '
            'background: #f0f0f0; padding: 6px 14px; border-radius: 6px; '
            'border: 2px solid #ddd; letter-spacing: 2px;">{}</span>',
            obj.code
        )
    code_display.short_description = 'Code Quitus'
    
    def montant_display(self, obj):
        """Affichage formaté du montant"""
        montant_str = "{:,.0f}".format(float(obj.montant)).replace(',', ' ')
        return format_html(
            '<span style="color: #2e7d32; font-weight: bold; font-size: 13px;">{} FCFA</span>',
            montant_str
        )
    montant_display.short_description = 'Montant'
    
    def statut_badge(self, obj):
        """Badge de statut coloré"""
        if obj.utilise:
            return format_html(
                '<span style="background: #f44336; color: white; padding: 5px 12px; '
                'border-radius: 14px; font-size: 11px; font-weight: bold;">✗ UTILISÉ</span>'
            )
        elif obj.date_expiration and obj.date_expiration < timezone.now():
            return format_html(
                '<span style="background: #ff9800; color: white; padding: 5px 12px; '
                'border-radius: 14px; font-size: 11px; font-weight: bold;">⏰ EXPIRÉ</span>'
            )
        else:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 5px 12px; '
                'border-radius: 14px; font-size: 11px; font-weight: bold;">✓ DISPONIBLE</span>'
            )
    statut_badge.short_description = 'Statut'
    
    def utilisateur_link(self, obj):
        """Lien vers l'utilisateur"""
        if obj.utilisateur:
            url = f'/admin/authentication/user/{obj.utilisateur.id}/change/'
            return format_html(
                '<a href="{}" style="font-weight: 500;">{}</a><br>'
                '<span style="color: #666; font-size: 11px;">{}</span>',
                url, obj.utilisateur.get_full_name(), obj.utilisateur.email
            )
        return format_html('<span style="color: #999;">Non utilisé</span>')
    utilisateur_link.short_description = 'Utilisé par'
    
    def expiration_info(self, obj):
        """Information sur l'expiration"""
        if obj.utilise:
            if obj.date_utilisation:
                return format_html(
                    '<span style="color: #666; font-weight: 500;">Utilisé le {}</span>',
                    obj.date_utilisation.strftime('%d/%m/%Y à %H:%M')
                )
            return '-'
        
        if not obj.date_expiration:
            return format_html('<span style="color: #999;">Pas d\'expiration</span>')
        
        maintenant = timezone.now()
        if obj.date_expiration < maintenant:
            jours_passes = (maintenant - obj.date_expiration).days
            return format_html(
                '<span style="color: #f44336; font-weight: 500;">⚠️ Expiré depuis {} jour(s)</span>',
                jours_passes
            )
        else:
            jours_restants = (obj.date_expiration - maintenant).days
            if jours_restants <= 7:
                color = '#ff9800'
                icon = '⚠️'
            elif jours_restants <= 30:
                color = '#ffa726'
                icon = '⏰'
            else:
                color = '#4caf50'
                icon = '✓'
            return format_html(
                '<span style="color: {}; font-weight: 500;">{} Expire dans {} jour(s)</span>',
                color, icon, jours_restants
            )
    expiration_info.short_description = 'Expiration'
    
    def stats_display(self, obj):
        """Afficher des statistiques dans le détail"""
        total = CodeQuitus.objects.count()
        disponibles = CodeQuitus.objects.filter(
            utilise=False, 
            date_expiration__gt=timezone.now()
        ).count()
        utilises = CodeQuitus.objects.filter(utilise=True).count()
        expires = CodeQuitus.objects.filter(
            date_expiration__lte=timezone.now(), 
            utilise=False
        ).count()
        
        pourcentage_utilises = (utilises / total * 100) if total > 0 else 0
        
        return format_html(
            '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'padding: 20px; border-radius: 10px; color: white;">'
            '<h3 style="margin: 0 0 15px 0; font-size: 16px;">📊 Statistiques Globales</h3>'
            '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">'
            
            '<div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">'
            '<div style="font-size: 24px; font-weight: bold;">{}</div>'
            '<div style="font-size: 11px; opacity: 0.9;">Total</div>'
            '</div>'
            
            '<div style="background: rgba(76,175,80,0.3); padding: 10px; border-radius: 8px;">'
            '<div style="font-size: 24px; font-weight: bold;">{}</div>'
            '<div style="font-size: 11px; opacity: 0.9;">Disponibles</div>'
            '</div>'
            
            '<div style="background: rgba(244,67,54,0.3); padding: 10px; border-radius: 8px;">'
            '<div style="font-size: 24px; font-weight: bold;">{}</div>'
            '<div style="font-size: 11px; opacity: 0.9;">Utilisés</div>'
            '</div>'
            
            '<div style="background: rgba(255,152,0,0.3); padding: 10px; border-radius: 8px;">'
            '<div style="font-size: 24px; font-weight: bold;">{}</div>'
            '<div style="font-size: 11px; opacity: 0.9;">Expirés</div>'
            '</div>'
            
            '</div>'
            '<div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px;">'
            '<div style="font-size: 12px; margin-bottom: 5px;">Taux d\'utilisation</div>'
            '<div style="background: rgba(255,255,255,0.2); height: 20px; border-radius: 10px; overflow: hidden;">'
            '<div style="background: #4caf50; height: 100%; width: {}%; '
            'display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold;">'
            '{:.1f}%</div>'
            '</div>'
            '</div>'
            '</div>',
            total, disponibles, utilises, expires, pourcentage_utilises, pourcentage_utilises
        )
    stats_display.short_description = 'Statistiques'
    
    def generer_codes_10(self, request, queryset):
        """Générer 10 codes"""
        codes = CodeQuitus.generer_batch(nombre=10)
        self.message_user(request, f'✅ {len(codes)} codes générés avec succès', level='success')
    generer_codes_10.short_description = '🎫 Générer 10 nouveaux codes'
    
    def generer_codes_50(self, request, queryset):
        """Générer 50 codes"""
        codes = CodeQuitus.generer_batch(nombre=50)
        self.message_user(request, f'✅ {len(codes)} codes générés avec succès', level='success')
    generer_codes_50.short_description = '🎫 Générer 50 nouveaux codes'
    
    def generer_codes_100(self, request, queryset):
        """Générer 100 codes"""
        codes = CodeQuitus.generer_batch(nombre=100)
        self.message_user(request, f'✅ {len(codes)} codes générés avec succès', level='success')
    generer_codes_100.short_description = '🎫 Générer 100 nouveaux codes'
    
    def has_add_permission(self, request):
        """Empêcher la création manuelle - utiliser les actions"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression des codes utilisés"""
        if obj and obj.utilise:
            return False
        return super().has_delete_permission(request, obj)


# ==========================================
# TRANSACTION BANCAIRE ADMIN
# ==========================================

@admin.register(TransactionBancaire)
class TransactionBancaireAdmin(admin.ModelAdmin):
    list_display = [
        'numero_recu', 
        'nom_payeur', 
        'code_quitus_link',
        'montant_display', 
        'date_paiement', 
        'banque_display'
    ]
    list_filter = ['banque', 'date_paiement', 'agence']
    search_fields = ['numero_recu', 'nom_payeur', 'code_quitus__code', 'agence']
    date_hierarchy = 'date_paiement'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('💳 Informations de Transaction', {
            'fields': ('numero_recu', 'code_quitus', 'nom_payeur', 'montant_paye')
        }),
        ('🏦 Informations Bancaires', {
            'fields': ('banque', 'agence', 'date_paiement')
        }),
        ('📝 Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('📅 Dates', {
            'fields': ('created_at',)
        }),
    )
    
    def code_quitus_link(self, obj):
        """Lien vers le code quitus"""
        url = f'/admin/authentication/codequitus/{obj.code_quitus.id}/change/'
        return format_html(
            '<a href="{}">'
            '<span style="font-family: monospace; font-weight: bold; font-size: 14px; '
            'background: #f0f0f0; padding: 4px 10px; border-radius: 4px;">{}</span></a>',
            url, obj.code_quitus.code
        )
    code_quitus_link.short_description = 'Code Quitus'
    
    def montant_display(self, obj):
        """Affichage formaté du montant"""
        montant_str = "{:,.0f}".format(float(obj.montant_paye)).replace(',', ' ')
        return format_html(
            '<span style="color: #2e7d32; font-weight: bold; font-size: 13px;">{} FCFA</span>',
            montant_str
        )
    montant_display.short_description = 'Montant'
    
    def banque_display(self, obj):
        """Affichage banque + agence"""
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="color: #666; font-size: 11px;">Agence: {}</span>',
            obj.banque, obj.agence
        )
    banque_display.short_description = 'Banque / Agence'


# ==========================================
# USER ACTION LOG ADMIN
# ==========================================

@admin.register(UserActionLog)
class UserActionLogAdmin(admin.ModelAdmin):
    list_display = ['action_badge', 'actor_display', 'target_display', 'created_at', 'ip_address']
    list_filter = ['action', 'created_at']
    search_fields = ['actor__email', 'target_user__email', 'ip_address']
    readonly_fields = ['actor', 'target_user', 'action', 'details', 'ip_address', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('👤 Acteurs', {
            'fields': ('actor', 'target_user')
        }),
        ('🎬 Action', {
            'fields': ('action', 'details')
        }),
        ('🌐 Technique', {
            'fields': ('ip_address', 'created_at')
        }),
    )
    
    def action_badge(self, obj):
        """Badge coloré selon l'action"""
        colors = {
            'create_user': '#4caf50',
            'update_user': '#2196f3',
            'delete_user': '#f44336',
            'reset_password': '#ff9800',
            'toggle_active': '#9c27b0',
            'assign_role': '#00bcd4',
        }
        color = colors.get(obj.action, '#757575')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 12px; '
            'border-radius: 14px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    
    def actor_display(self, obj):
        """Affichage de l'acteur"""
        if obj.actor:
            url = f'/admin/authentication/user/{obj.actor.id}/change/'
            return format_html(
                '<a href="{}" style="font-weight: 500;">{}</a><br>'
                '<span style="color: #666; font-size: 11px;">{}</span>',
                url, obj.actor.get_full_name(), obj.actor.email
            )
        return format_html('<span style="color: #999;">Système</span>')
    actor_display.short_description = 'Effectué par'
    
    def target_display(self, obj):
        """Affichage de la cible"""
        if obj.target_user:
            url = f'/admin/authentication/user/{obj.target_user.id}/change/'
            return format_html(
                '<a href="{}" style="font-weight: 500;">{}</a><br>'
                '<span style="color: #666; font-size: 11px;">{}</span>',
                url, obj.target_user.get_full_name(), obj.target_user.email
            )
        return format_html('<span style="color: #999;">-</span>')
    target_display.short_description = 'Cible'
    
    def has_add_permission(self, request):
        """Les logs ne peuvent pas être créés manuellement"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Les logs ne peuvent pas être modifiés"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Seuls les super admins peuvent supprimer les logs"""
        return request.user.is_superuser


# Configuration de l'admin site
admin.site.site_header = "Administration SGEE"
admin.site.site_title = "SGEE Admin"
admin.site.index_title = "Panneau d'administration"
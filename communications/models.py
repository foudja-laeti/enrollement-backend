from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Categorie(models.Model):
    TYPE_CHOICES = [
        ('actualite', 'Actualité'),
        ('document', 'Document'),
        ('notification', 'Notification'),
    ]

    nom = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    couleur = models.CharField(max_length=7, blank=True, null=True, help_text="Code couleur hex")
    icone = models.CharField(max_length=50, blank=True, null=True, help_text="Nom de l'icône")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return f"{self.nom} ({self.get_type_display()})"

class Epreuve(models.Model):
    """Anciennes épreuves d'examens"""
    
    titre = models.CharField(max_length=255, verbose_name='Titre')
    slug = models.SlugField(max_length=191, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    # ✅ UNIQUEMENT : Filiere (ForeignKey) + Année
    filiere = models.ForeignKey('configurations.Filiere', on_delete=models.CASCADE, related_name='epreuves')
    annee = models.IntegerField(verbose_name='Année')
    
    # ✅ Fichier
    fichier = models.FileField(upload_to='epreuves/%Y/%m/%d/', verbose_name='Fichier PDF')
    taille = models.CharField(max_length=20, blank=True, verbose_name='Taille')
    
    # ✅ Statistiques
    nombre_telechargements = models.IntegerField(default=0)
    
    # ✅ Publication
    is_published = models.BooleanField(default=True, verbose_name='Publié')
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='epreuves'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'epreuves'
        verbose_name = 'Épreuve'
        verbose_name_plural = 'Épreuves'
        ordering = ['-annee', 'filiere']
        indexes = [
            models.Index(fields=['filiere', 'annee']),
            models.Index(fields=['is_published']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.annee} ({self.filiere})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.titre}-{self.annee}-{self.filiere}")[:191]
        
        if self.fichier and not self.taille:
            size_mb = self.fichier.size / (1024 * 1024)
            self.taille = f"{size_mb:.1f} MB"
        
        super().save(*args, **kwargs)
    
    def incrementer_telechargements(self):
        self.nombre_telechargements += 1
        self.save(update_fields=['nombre_telechargements'])

class Actualite(models.Model):
    titre = models.CharField(max_length=255)
    slug = models.SlugField(max_length=191, unique=True, blank=True)  # ← CHANGÉ : 191 au lieu de 255
    contenu = models.TextField()
    extrait = models.TextField(blank=True, null=True, help_text="Résumé court")
    image_path = models.CharField(max_length=255, blank=True, null=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True, related_name='actualites')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actualites')
    
    # Publication
    is_published = models.BooleanField(default=False)
    date_publication = models.DateTimeField(null=True, blank=True)
    
    # SEO
    meta_description = models.CharField(max_length=255, blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Statistiques
    vues = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'actualite'
        verbose_name = 'Actualité'
        verbose_name_plural = 'Actualités'
        ordering = ['-date_publication', '-created_at']
        indexes = [
            models.Index(fields=['is_published']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        # Générer le slug automatiquement si non défini
        if not self.slug:
            self.slug = slugify(self.titre)[:191]  # ← AJOUTÉ : Limiter à 191 caractères
        super().save(*args, **kwargs)

    def incrementer_vues(self):
        """Incrémenter le nombre de vues"""
        self.vues += 1
        self.save(update_fields=['vues'])

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Succès'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    lien = models.CharField(max_length=255, blank=True, null=True, help_text="Lien vers une page")
    
    # Lecture
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.titre} - {self.user.email}"

    def marquer_comme_lu(self):
        """Marquer la notification comme lue"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=100, help_text="CREATE, UPDATE, DELETE, LOGIN")
    table_name = models.CharField(max_length=100, blank=True, null=True)
    record_id = models.BigIntegerField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True, help_text="Anciennes valeurs")
    new_values = models.JSONField(null=True, blank=True, help_text="Nouvelles valeurs")
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'audit_log'
        verbose_name = 'Journal d\'Audit'
        verbose_name_plural = 'Journaux d\'Audit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['table_name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else 'Anonyme'
        return f"{self.action} - {self.table_name} - {user_email}"
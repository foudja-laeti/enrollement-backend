from django.db import models
from django.conf import settings
from django.utils import timezone
from candidats.models import Candidat, Dossier
from configurations.models import AnneeScolaire, Filiere, Niveau, CentreExamen, CentreDepot, Diplome
import random
import string


class Inscription(models.Model):
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis'),
        ('en_attente', 'En Attente'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    MENTION_CHOICES = [
        ('Passable', 'Passable'),
        ('AB', 'Assez Bien'),
        ('B', 'Bien'),
        ('TB', 'Très Bien'),
    ]

    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name='inscriptions')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='inscriptions')
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, related_name='inscriptions')
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name='inscriptions')
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='inscriptions')
    centre_examen = models.ForeignKey(CentreExamen, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscriptions')
    centre_depot = models.ForeignKey(CentreDepot, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscriptions')
    
    # Informations académiques
    diplome = models.ForeignKey(Diplome, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscriptions')
    serie = models.CharField(max_length=100, blank=True, null=True, help_text="A, C, D, etc.")
    annee_obtention_diplome = models.IntegerField(null=True, blank=True)
    pays_obtention_diplome = models.CharField(max_length=100, blank=True, null=True)
    etablissement_origine = models.CharField(max_length=255, blank=True, null=True)
    ville_etablissement = models.CharField(max_length=100, blank=True, null=True)
    moyenne_generale = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    mention = models.CharField(max_length=50, choices=MENTION_CHOICES, blank=True, null=True)
    
    # Statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    numero_inscription = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Numéro d'inscription généré")
    qr_code_path = models.CharField(max_length=255, blank=True, null=True, help_text="Chemin du QR code")
    fiche_inscription_path = models.CharField(max_length=255, blank=True, null=True, help_text="Chemin de la fiche PDF")
    
    # Validation
    date_soumission = models.DateTimeField(null=True, blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscriptions_validees')
    motif_rejet = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inscription'
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'
        indexes = [
            models.Index(fields=['candidat']),
            models.Index(fields=['statut']),
            models.Index(fields=['numero_inscription']),
            models.Index(fields=['filiere']),
            models.Index(fields=['niveau']),
        ]

    def __str__(self):
        return f"{self.numero_inscription} - {self.candidat.nom} - {self.filiere.code}"

    def save(self, *args, **kwargs):
        # Générer le numéro d'inscription si non défini
        if not self.numero_inscription:
            self.numero_inscription = self.generer_numero_inscription()
        super().save(*args, **kwargs)

    @staticmethod
    def generer_numero_inscription():
        """Générer un numéro d'inscription unique"""
        import datetime
        annee = datetime.datetime.now().year
        code = ''.join(random.choices(string.digits, k=6))
        return f"INS{annee}{code}"
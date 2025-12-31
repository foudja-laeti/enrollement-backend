from django.db import models
from django.conf import settings
from django.utils import timezone
from configurations.models import AnneeScolaire
from authentication.models import CodeQuitus 
import random
import string

class Region(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom

class Departement(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='departements')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} ({self.region.nom})"

class Quitus(models.Model):
    code = models.CharField(max_length=6, unique=True, help_text="Code à 6 chiffres")
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, related_name='quitus')
    banque = models.CharField(max_length=100, blank=True, null=True, help_text="Nom de la banque")
    reference_paiement = models.CharField(max_length=100, blank=True, null=True, help_text="Référence bancaire")
    date_paiement = models.DateField(null=True, blank=True, help_text="Date du paiement")
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey('Candidat', on_delete=models.SET_NULL, null=True, blank=True, related_name='quitus_utilise')
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quitus'
        verbose_name = 'Quitus'
        verbose_name_plural = 'Quitus'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_used']),
        ]

    def __str__(self):
        return f"Quitus {self.code} - {'Utilisé' if self.is_used else 'Disponible'}"

    def marquer_utilise(self, candidat):
        """Marquer le quitus comme utilisé par un candidat"""
        self.is_used = True
        self.used_by = candidat
        self.used_at = timezone.now()
        self.save()

class Candidat(models.Model):
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    STATUT_CHOICES = [
        ('incomplet', 'Incomplet'),
        ('complet', 'Complet'),
        ('en_attente', 'En Attente'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidat')
    code_quitus = models.ForeignKey(
        'authentication.CodeQuitus', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='candidat'
    )
    matricule = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # ✅ Informations personnelles
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=255)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    nationalite = models.CharField(max_length=100, default='Camerounaise')
    telephone = models.CharField(max_length=20, blank=True, null=True)
    telephone_secondaire = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=191)
    
    # ✅ Parents/Tuteur
    nom_pere = models.CharField(max_length=100, blank=True, null=True)
    tel_pere = models.CharField(max_length=20, blank=True, null=True)
    profession_pere = models.CharField(max_length=100, blank=True, null=True)
    nom_mere = models.CharField(max_length=100, blank=True, null=True)
    tel_mere = models.CharField(max_length=20, blank=True, null=True)
    profession_mere = models.CharField(max_length=100, blank=True, null=True)
    nom_tuteur = models.CharField(max_length=100, blank=True, null=True)
    telephone_tuteur = models.CharField(max_length=20, blank=True, null=True)
    
    # ✅ Adresse
    adresse_actuelle = models.TextField(blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    quartier = models.CharField(max_length=100, blank=True, null=True)
    region = models.ForeignKey('Region', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    departement = models.ForeignKey('Departement', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    pays = models.CharField(max_length=100, default='Cameroun')
    boite_postale = models.CharField(max_length=50, blank=True, null=True)
    
    # ✅ NOUVEAU : ForeignKeys pour configurations académiques
    bac = models.ForeignKey('configurations.Bac', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    serie = models.ForeignKey('configurations.Serie', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    mention = models.ForeignKey('configurations.Mention', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    filiere = models.ForeignKey('configurations.Filiere', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    niveau = models.ForeignKey('configurations.Niveau', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    centre_examen = models.ForeignKey('configurations.CentreExamen', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    centre_depot = models.ForeignKey('configurations.CentreDepot', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidats')
    
    # ✅ NOUVEAU : Champ texte pour établissement d'origine
    etablissement_origine = models.CharField(max_length=255, blank=True, null=True)
    annee_obtention_diplome = models.IntegerField(null=True, blank=True)
    
    # ✅ Documents (chemins)
    photo_path = models.CharField(max_length=255, blank=True, null=True)
    
    # Statut
    statut_dossier = models.CharField(max_length=20, choices=STATUT_CHOICES, default='incomplet')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'candidat'
        verbose_name = 'Candidat'
        verbose_name_plural = 'Candidats'
        indexes = [
            models.Index(fields=['matricule']),
            models.Index(fields=['nom', 'prenom']),
            models.Index(fields=['statut_dossier']),
        ]

    def __str__(self):
        return f"{self.matricule} - {self.nom} {self.prenom}"

    def save(self, *args, **kwargs):
        if not self.matricule:
            self.matricule = self.generer_matricule()
        super().save(*args, **kwargs)

    @staticmethod
    def generer_matricule():
        import datetime
        annee = datetime.datetime.now().year
        code = ''.join(random.choices(string.digits, k=5))
        return f"CAND{annee}{code}"
class Dossier(models.Model):
    STATUT_CHOICES = [
        ('ouvert', 'Ouvert'),
        ('en_cours', 'En Cours'),
        ('complet', 'Complet'),
        ('soumis', 'Soumis'),
        ('valide', 'Validé'),
        ('cloture', 'Clôturé'),
    ]

    candidat = models.OneToOneField(Candidat, on_delete=models.CASCADE, related_name='dossier')
    numero_dossier = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Numéro unique du dossier")
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, related_name='dossiers')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='ouvert')
    date_ouverture = models.DateTimeField(default=timezone.now)
    date_soumission = models.DateTimeField(null=True, blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    observations = models.TextField(blank=True, null=True, help_text="Remarques administratives")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dossier'
        verbose_name = 'Dossier'
        verbose_name_plural = 'Dossiers'
        indexes = [
            models.Index(fields=['numero_dossier']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"Dossier {self.numero_dossier} - {self.candidat.nom}"

    def save(self, *args, **kwargs):
        if not self.numero_dossier:
            self.numero_dossier = self.generer_numero_dossier()
        super().save(*args, **kwargs)

    @staticmethod
    def generer_numero_dossier():
        import datetime
        annee = datetime.datetime.now().year
        code = ''.join(random.choices(string.digits, k=5))
        return f"DOS{annee}{code}"

class Document(models.Model):
    TYPE_CHOICES = [
        ('acte_naissance', 'Acte de Naissance'),
        ('diplome', 'Diplôme'),
        ('releve_notes', 'Relevé de Notes'),
        ('photo_identite', 'Photo d\'Identité'),
        ('certificat_nationalite', 'Certificat de Nationalité'),
        ('quitus_paiement', 'Quitus de Paiement'),
        ('certificat_inscription', 'Certificat d\'Inscription'),
        ('attestation_reussite', 'Attestation de Réussite'),
        ('autre', 'Autre'),
    ]

    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name='documents')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    inscription = models.ForeignKey('inscriptions.Inscription', on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    
    type_document = models.CharField(max_length=50, choices=TYPE_CHOICES)
    nom_fichier = models.CharField(max_length=255)
    nom_original = models.CharField(max_length=255)
    chemin_fichier = models.CharField(max_length=255)
    taille_fichier = models.IntegerField(null=True, blank=True, help_text="Taille en octets")
    extension = models.CharField(max_length=10, blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Validation
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents_verifies')
    verified_at = models.DateTimeField(null=True, blank=True)
    commentaire_verification = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        indexes = [
            models.Index(fields=['type_document']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return f"{self.get_type_document_display()} - {self.candidat.nom}"

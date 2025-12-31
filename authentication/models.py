# authentication/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import secrets

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrateur'),
        ('admin_academique', 'Administrateur Académique'),
        ('responsable_filiere', 'Responsable de Filière'),
        ('candidat', 'Candidat'),
    ]
    
    email = models.EmailField(max_length=191, unique=True)
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='candidat')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created',
        verbose_name='Créé par'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.prenom} {self.nom}".strip() or self.email
    
    def get_role_display_custom(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def can_create_role(self, target_role):
        """Vérifie si l'utilisateur peut créer un utilisateur avec ce rôle"""
        permissions = {
            'super_admin': ['admin_academique', 'responsable_filiere'],
            'admin_academique': ['responsable_filiere'],
            'responsable_filiere': [],
            'candidat': [],
        }
        return target_role in permissions.get(self.role, [])
    
    def can_manage_user(self, target_user):
        """Vérifie si l'utilisateur peut gérer cet utilisateur"""
        if self.role == 'super_admin':
            return target_user.role != 'super_admin'
        elif self.role == 'admin_academique':
            return target_user.role in ['responsable_filiere', 'candidat']
        elif self.role == 'responsable_filiere':
            return target_user.role == 'candidat' and hasattr(target_user, 'candidat')
        return False


class ResponsableFiliere(models.Model):
    """Informations supplémentaires pour les responsables de filière"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='responsable_filiere_profile'
    )
    filiere = models.ForeignKey(
        'configurations.Filiere',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsables'
    )
    telephone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'responsables_filiere'
        verbose_name = 'Responsable de Filière'
        verbose_name_plural = 'Responsables de Filière'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.filiere}"


class CodeQuitus(models.Model):
    """Codes générés pour la banque - permettent l'inscription"""
    code = models.CharField(max_length=6, unique=True, db_index=True, verbose_name='Code Quitus')
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=50000, verbose_name='Montant (FCFA)')
    date_generation = models.DateTimeField(auto_now_add=True, verbose_name='Date de génération')
    date_expiration = models.DateTimeField(verbose_name='Date d\'expiration')
    utilise = models.BooleanField(default=False, verbose_name='Utilisé')
    utilisateur = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='codes_quitus',
        verbose_name='Utilisateur'
    )
    date_utilisation = models.DateTimeField(null=True, blank=True, verbose_name='Date d\'utilisation')
    reference_bancaire = models.CharField(max_length=50, unique=True, verbose_name='Référence bancaire')
    
    class Meta:
        db_table = 'codes_quitus'
        verbose_name = 'Code Quitus'
        verbose_name_plural = 'Codes Quitus'
        ordering = ['-date_generation']
        indexes = [
            models.Index(fields=['code', 'utilise']),
            models.Index(fields=['date_expiration']),
        ]
    
    def __str__(self):
        status = 'Utilisé' if self.utilise else 'Disponible'
        return f"{self.code} - {status}"
    
    @classmethod
    def generer_batch(cls, nombre=100, montant=50000, validite_jours=90):
        """Générer un lot de codes pour la banque"""
        codes = []
        date_expiration = timezone.now() + timezone.timedelta(days=validite_jours)
        
        for _ in range(nombre):
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            while cls.objects.filter(code=code).exists():
                code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            ref_bancaire = f"REF{timezone.now().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"
            
            codes.append(cls(
                code=code,
                montant=montant,
                date_expiration=date_expiration,
                reference_bancaire=ref_bancaire
            ))
        
        cls.objects.bulk_create(codes)
        return codes
    
    def marquer_utilise(self, utilisateur):
        """Marquer le code comme utilisé par un utilisateur"""
        self.utilise = True
        self.utilisateur = utilisateur
        self.date_utilisation = timezone.now()
        self.save(update_fields=['utilise', 'utilisateur', 'date_utilisation'])
    
    def est_valide(self):
        """Vérifier si le code est encore valide"""
        return not self.utilise and self.date_expiration > timezone.now()


class TransactionBancaire(models.Model):
    """Historique des transactions bancaires"""
    code_quitus = models.OneToOneField(
        CodeQuitus, 
        on_delete=models.CASCADE,
        related_name='transaction',
        verbose_name='Code Quitus'
    )
    nom_payeur = models.CharField(max_length=200, verbose_name='Nom du payeur')
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant payé')
    date_paiement = models.DateTimeField(verbose_name='Date de paiement')
    banque = models.CharField(max_length=100, verbose_name='Banque')
    agence = models.CharField(max_length=100, verbose_name='Agence')
    numero_recu = models.CharField(max_length=50, unique=True, verbose_name='Numéro de reçu')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions_bancaires'
        verbose_name = 'Transaction Bancaire'
        verbose_name_plural = 'Transactions Bancaires'
        ordering = ['-date_paiement']
    
    def __str__(self):
        return f"{self.numero_recu} - {self.nom_payeur}"


class UserActionLog(models.Model):
    """Log des actions des utilisateurs (pour l'archivage)"""
    ACTION_CHOICES = [
        ('create_user', 'Création utilisateur'),
        ('update_user', 'Modification utilisateur'),
        ('delete_user', 'Suppression utilisateur'),
        ('reset_password', 'Réinitialisation mot de passe'),
        ('toggle_active', 'Activation/Désactivation compte'),
        ('assign_role', 'Attribution rôle'),
    ]
    
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actions_performed',
        verbose_name='Acteur'
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actions_received',
        verbose_name='Utilisateur cible'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_action_logs'
        verbose_name = 'Log Action Utilisateur'
        verbose_name_plural = 'Logs Actions Utilisateurs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.actor} - {self.get_action_display()} - {self.created_at}"
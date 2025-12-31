from django.db import models
from django.utils import timezone


class AnneeScolaire(models.Model):
    libelle = models.CharField(max_length=50, unique=True, help_text="Ex: 2024-2025")
    date_debut = models.DateField()
    date_fin = models.DateField()
    date_debut_inscription = models.DateField(null=True, blank=True)
    date_fin_inscription = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False, help_text="Une seule année active à la fois")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'annee_scolaire'
        verbose_name = 'Année Scolaire'
        verbose_name_plural = 'Années Scolaires'
        ordering = ['-date_debut']

    def __str__(self):
        return self.libelle


class Niveau(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Ex: L1, L3")
    libelle = models.CharField(max_length=100, help_text="Ex: Première Année")
    ordre = models.IntegerField(unique=True, help_text="1, 3, etc.")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'niveau'
        verbose_name = 'Niveau'
        verbose_name_plural = 'Niveaux'
        ordering = ['ordre']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class Filiere(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Ex: INF, GC, GM")
    libelle = models.CharField(max_length=255, help_text="Ex: Informatique")
    description = models.TextField(blank=True, null=True)
    duree_annees = models.IntegerField(default=3, help_text="Durée en années")
    frais_inscription = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'filiere'
        verbose_name = 'Filière'
        verbose_name_plural = 'Filières'

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class FiliereNiveau(models.Model):
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name='filiere_niveaux')
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='filiere_niveaux')
    places_disponibles = models.IntegerField(default=0)
    places_occupees = models.IntegerField(default=0)
    frais_scolarite = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'filiere_niveau'
        verbose_name = 'Filière-Niveau'
        verbose_name_plural = 'Filières-Niveaux'
        unique_together = ['filiere', 'niveau']

    def __str__(self):
        return f"{self.filiere.code} - {self.niveau.code}"


class Diplome(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Ex: BAC, LICENCE")
    libelle = models.CharField(max_length=255, help_text="Ex: Baccalauréat")
    niveau_etude = models.CharField(max_length=100, blank=True, null=True, help_text="Secondaire, Supérieur")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'diplome'
        verbose_name = 'Diplôme'
        verbose_name_plural = 'Diplômes'

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class FiliereDiplome(models.Model):
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name='diplomes_requis')
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='diplomes_requis')
    diplome = models.ForeignKey(Diplome, on_delete=models.CASCADE, related_name='filieres')
    is_required = models.BooleanField(default=True, help_text="Diplôme obligatoire ou optionnel")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'filiere_diplome'
        verbose_name = 'Filière-Diplôme'
        verbose_name_plural = 'Filières-Diplômes'
        unique_together = ['filiere', 'niveau', 'diplome']

    def __str__(self):
        return f"{self.filiere.code} - {self.niveau.code} - {self.diplome.code}"


class CentreExamen(models.Model):
    code = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    capacite = models.IntegerField(default=0, help_text="Nombre de places")
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=191, blank=True, null=True)
    responsable = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centre_examen'
        verbose_name = 'Centre d\'Examen'
        verbose_name_plural = 'Centres d\'Examen'

    def __str__(self):
        return f"{self.code} - {self.nom}"

class Region(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
class Departement(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.nom

class CentreDepot(models.Model):
    code = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=191, blank=True, null=True)
    responsable = models.CharField(max_length=255, blank=True, null=True)
    horaires = models.TextField(blank=True, null=True, help_text="Horaires d'ouverture")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centre_depot'
        verbose_name = 'Centre de Dépôt'
        verbose_name_plural = 'Centres de Dépôt'

    def __str__(self):
        return f"{self.code} - {self.nom}"

class Bac(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Ex: A4, C, D")
    libelle = models.CharField(max_length=255, help_text="Ex: Baccalauréat A4")
    created_at = models.DateTimeField(default=timezone.now)

class Serie(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Ex: A1, A2, C1")
    libelle = models.CharField(max_length=255)
    bac = models.ForeignKey(Bac, on_delete=models.CASCADE, related_name='series')
    created_at = models.DateTimeField(default=timezone.now)

# configurations/models.py

# configurations/models.py

class Mention(models.Model):
    bac = models.ForeignKey(
        'Bac', 
        on_delete=models.CASCADE, 
        related_name='mentions',
        help_text="BAC auquel appartient cette mention"
    )  # ✅ Ferme correctement la parenthèse
    
    code = models.CharField(max_length=20, help_text="Ex: TB, B, AB, PASSABLE")
    libelle = models.CharField(max_length=100, help_text="Ex: Très Bien, Bien, Assez Bien")
    
    # Pour BAC français (notes sur 20)
    minimum_points = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Points minimum (ex: 10.00 pour Passable)"
    )
    maximum_points = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Points maximum (ex: 11.99 pour Passable)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mention'
        verbose_name = 'Mention'
        verbose_name_plural = 'Mentions'
        unique_together = ['bac', 'code']
        ordering = ['bac', 'minimum_points']  # ✅ Pas de help_text ici !

    def __str__(self):
        if self.minimum_points and self.maximum_points:
            return f"{self.bac.code} - {self.libelle} ({self.minimum_points}-{self.maximum_points})"
        return f"{self.bac.code} - {self.libelle}"
class SerieFiliere(models.Model):  # Table de liaison Serie → Filiere
    serie = models.ForeignKey(Serie, on_delete=models.CASCADE, related_name='filieres')
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name='series')
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='series_filieres')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['serie', 'filiere', 'niveau']

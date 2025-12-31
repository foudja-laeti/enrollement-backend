# inscriptions/serializers.py
from rest_framework import serializers
from candidats.models import Candidat, Dossier, Document, Quitus
from configurations.models import (
    AnneeScolaire, Filiere, Niveau, CentreExamen, CentreDepot, Diplome
)
from .models import Inscription
from django.utils import timezone
from django.db import transaction


class CandidatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidat
        fields = [
            "id", "nom", "prenom", "date_naissance", "lieu_naissance",
            "sexe", "nationalite", "telephone", "telephone_secondaire",
            "email", "nom_pere", "telephone_pere", "profession_pere",
            "nom_mere", "telephone_mere", "profession_mere",
            "nom_tuteur", "telephone_tuteur",
            "adresse_actuelle", "ville", "region", "pays", "boite_postale",
        ]
        read_only_fields = ["id", "pays"]  # pays par défaut Cameroun
        
class InscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscription
        fields = [
            "id", "filiere", "niveau", "centre_examen", "centre_depot",
            "diplome", "serie", "annee_obtention_diplome",
            "pays_obtention_diplome", "etablissement_origine",
            "ville_etablissement", "moyenne_generale", "mention",
        ]
        read_only_fields = ["id"]
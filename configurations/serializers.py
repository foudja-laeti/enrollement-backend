from rest_framework import serializers
from candidats.models import Region, Departement
from .models import (
    Filiere, Niveau, Diplome, CentreExamen, CentreDepot,
    Bac, Serie, Mention, SerieFiliere
)

# ✅ EXISTANTS (tes serializers)
class FiliereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiere
        fields = ["id", "code", "libelle", "description", "duree_annees", "frais_inscription", "is_active"]

class NiveauSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niveau
        fields = ["id", "code", "libelle", "ordre", "description"]

class DiplomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diplome
        fields = ["id", "code", "libelle", "niveau_etude", "description"]

class CentreExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentreExamen
        fields = ["id", "code", "nom", "ville", "region", "is_active"]

class CentreDepotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentreDepot
        fields = ["id", "code", "nom", "ville", "region", "is_active"]

# ✅ NOUVEAUX (pour tes vues BAC/SERIE)
class BacSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bac
        fields = ["id", "code", "libelle"]

class SerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Serie
        fields = ["id", "code", "libelle", "bac"]

# configurations/serializers.py

class MentionSerializer(serializers.ModelSerializer):
    bac_code = serializers.CharField(source='bac.code', read_only=True)
    
    class Meta:
        model = Mention
        fields = [
            "id", "bac", "bac_code", "code", "libelle", 
            "minimum_points", "maximum_points", "is_active"
        ]

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'nom', 'code']

class DepartementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departement
        fields = ['id', 'nom', 'code', 'region']
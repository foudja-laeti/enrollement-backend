from rest_framework import generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from candidats.models import Region, Departement
from .serializers import RegionSerializer, DepartementSerializer 
from django.shortcuts import get_object_or_404
from .models import (
    Filiere, Niveau, Diplome, CentreExamen, CentreDepot,
    Bac, Serie, Mention, SerieFiliere
)
from .serializers import (
    FiliereSerializer, NiveauSerializer, DiplomeSerializer,
    CentreExamenSerializer, CentreDepotSerializer,
    BacSerializer, SerieSerializer, MentionSerializer
)

# VUES LISTES SIMPLES
class FiliereListView(generics.ListAPIView):
    queryset = Filiere.objects.filter(is_active=True)
    serializer_class = FiliereSerializer
    permission_classes = [permissions.AllowAny]

class NiveauListView(generics.ListAPIView):
    queryset = Niveau.objects.all().order_by('ordre')
    serializer_class = NiveauSerializer
    permission_classes = [permissions.AllowAny]

class DiplomeListView(generics.ListAPIView):
    queryset = Diplome.objects.all()
    serializer_class = DiplomeSerializer
    permission_classes = [permissions.AllowAny]

class CentreExamenListView(generics.ListAPIView):
    queryset = CentreExamen.objects.filter(is_active=True)
    serializer_class = CentreExamenSerializer
    permission_classes = [permissions.AllowAny]

class CentreDepotListView(generics.ListAPIView):
    queryset = CentreDepot.objects.filter(is_active=True)
    serializer_class = CentreDepotSerializer
    permission_classes = [permissions.AllowAny]

class BacListView(generics.ListAPIView):
    queryset = Bac.objects.all()
    serializer_class = BacSerializer
    permission_classes = [permissions.AllowAny]

class SerieListView(generics.ListAPIView):
    queryset = Serie.objects.all()
    serializer_class = SerieSerializer
    permission_classes = [permissions.AllowAny]

class MentionListView(generics.ListAPIView):
    queryset = Mention.objects.filter(is_active=True)
    serializer_class = MentionSerializer
    permission_classes = [permissions.AllowAny]

# ✅ TES FONCTIONS CASCADES (maintenant définies !)
@api_view(['GET'])
def series_by_bac(request, bac_id):
    series = Serie.objects.filter(bac_id=bac_id)
    serializer = SerieSerializer(series, many=True)
    return Response(serializer.data)

# views.py - VERSION CORRIGÉE
@api_view(['GET'])
def filieres_by_serie(request, serie_id):
    """Retourne les filières accessibles via une série donnée"""
    serie_filieres = SerieFiliere.objects.filter(serie_id=serie_id)
    filieres = Filiere.objects.filter(
        id__in=serie_filieres.values_list('filiere_id', flat=True)
    ).filter(is_active=True).distinct()
    
    serializer = FiliereSerializer(filieres, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def niveaux_by_serie_filiere(request, serie_id, filiere_id):
    serie_filieres = SerieFiliere.objects.filter(serie_id=serie_id, filiere_id=filiere_id)
    niveaux = Niveau.objects.filter(series_filieres__in=serie_filieres).distinct().order_by('ordre')
    serializer = NiveauSerializer(niveaux, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def diplomes_by_niveau_filiere(request, niveau_id, filiere_id):
    diplomes = Diplome.objects.filter(
        filieres__filiere_id=filiere_id,
        filieres__niveau_id=niveau_id
    ).distinct()
    serializer = DiplomeSerializer(diplomes, many=True)
    return Response(serializer.data)

# configurations/views.py

@api_view(['GET'])
def mentions_by_bac(request, bac_id):
    """Retourne les mentions d'un BAC donné"""
    mentions = Mention.objects.filter(bac_id=bac_id, is_active=True)
    serializer = MentionSerializer(mentions, many=True)
    return Response(serializer.data)

class RegionListView(generics.ListAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

class DepartementListView(generics.ListAPIView):
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer
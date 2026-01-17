# ============================================
# 1. configurations/views.py - CORRIGER LES IMPORTS
# ============================================
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
import csv

from candidats.models import Region, Departement, Candidat
from authentication.permissions import IsAdminAcademique
from .models import (
    Filiere, Niveau, Diplome, CentreExamen, CentreDepot,
    Bac, Serie, Mention, SerieFiliere
)
from .serializers import (
    FiliereSerializer, NiveauSerializer, DiplomeSerializer,
    CentreExamenSerializer, CentreDepotSerializer,
    BacSerializer, SerieSerializer, MentionSerializer,
    RegionSerializer, DepartementSerializer
)

class FiliereViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion complète des filières
    Accessible uniquement aux admins académiques
    """
    permission_classes = [IsAuthenticated, IsAdminAcademique]

    def list(self, request):
        """Liste des filières avec filtres"""
        try:
            is_active = request.query_params.get('is_active')
            
            filieres = Filiere.objects.all()
            
            # Filtre par statut
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                filieres = filieres.filter(is_active=is_active_bool)
            
            # Annoter avec le nombre de candidats
            filieres = filieres.annotate(
                total_candidats=Count('candidat'),
                candidats_valides=Count('candidat', filter=Q(candidat__statut_dossier='valide'))
            )
            
            data = []
            for filiere in filieres:
                data.append({
                    'id': filiere.id,
                    'code': filiere.code,
                    'libelle': filiere.libelle,
                    'description': filiere.description if hasattr(filiere, 'description') else None,
                    'quota': filiere.quota if hasattr(filiere, 'quota') else None,
                    'is_active': filiere.is_active,
                    'total_candidats': filiere.total_candidats,
                    'candidats_valides': filiere.candidats_valides,
                    'created_at': filiere.created_at if hasattr(filiere, 'created_at') else None,
                })
            
            return Response(data)
            
        except Exception as e:
            print(f"❌ Erreur liste filières: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """Créer une nouvelle filière"""
        try:
            code = request.data.get('code', '').strip()
            libelle = request.data.get('libelle', '').strip()
            description = request.data.get('description', '').strip()
            quota = request.data.get('quota')
            
            # Validation
            if not code or not libelle:
                return Response(
                    {'error': 'Le code et le libellé sont obligatoires'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier unicité du code
            if Filiere.objects.filter(code=code).exists():
                return Response(
                    {'code': ['Ce code de filière existe déjà']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Créer la filière
            filiere = Filiere.objects.create(
                code=code,
                libelle=libelle,
                is_active=True
            )
            
            # Ajouter les champs optionnels s'ils existent
            if hasattr(filiere, 'description'):
                filiere.description = description
            
            if hasattr(filiere, 'quota') and quota:
                try:
                    filiere.quota = int(quota)
                except ValueError:
                    pass
            
            filiere.save()
            
            return Response({
                'id': filiere.id,
                'code': filiere.code,
                'libelle': filiere.libelle,
                'message': 'Filière créée avec succès'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ Erreur création filière: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Détails d'une filière"""
        try:
            filiere = Filiere.objects.get(id=pk)
            
            # Statistiques
            candidats = Candidat.objects.filter(filiere=filiere)
            
            # Responsable
            from authentication.models import ResponsableFiliere
            resp_filiere = ResponsableFiliere.objects.filter(
                filiere=filiere
            ).select_related('user').first()
            
            responsable_info = None
            if resp_filiere and resp_filiere.user:
                responsable_info = {
                    'id': resp_filiere.user.id,
                    'nom': resp_filiere.user.nom,
                    'prenom': resp_filiere.user.prenom,
                    'email': resp_filiere.user.email,
                }
            
            data = {
                'id': filiere.id,
                'code': filiere.code,
                'libelle': filiere.libelle,
                'description': filiere.description if hasattr(filiere, 'description') else None,
                'quota': filiere.quota if hasattr(filiere, 'quota') else None,
                'is_active': filiere.is_active,
                'created_at': filiere.created_at if hasattr(filiere, 'created_at') else None,
                'responsable': responsable_info,
                'statistiques': {
                    'total_candidats': candidats.count(),
                    'valides': candidats.filter(statut_dossier='valide').count(),
                    'en_attente': candidats.filter(statut_dossier__in=['en_attente', 'complet']).count(),
                    'rejetes': candidats.filter(statut_dossier='rejete').count(),
                }
            }
            
            return Response(data)
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Erreur détails filière: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, pk=None):
        """Modifier une filière (PUT = complet)"""
        try:
            filiere = Filiere.objects.get(id=pk)
            
            # Mettre à jour les champs
            if 'code' in request.data:
                new_code = request.data['code'].strip()
                # Vérifier unicité sauf pour cette filière
                if Filiere.objects.filter(code=new_code).exclude(id=pk).exists():
                    return Response(
                        {'code': ['Ce code existe déjà']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                filiere.code = new_code
            
            if 'libelle' in request.data:
                filiere.libelle = request.data['libelle'].strip()
            
            if hasattr(filiere, 'description') and 'description' in request.data:
                filiere.description = request.data['description']
            
            if hasattr(filiere, 'quota') and 'quota' in request.data:
                try:
                    filiere.quota = int(request.data['quota'])
                except ValueError:
                    return Response(
                        {'quota': ['Quota invalide']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if 'is_active' in request.data:
                filiere.is_active = request.data['is_active']
            
            filiere.save()
            
            return Response({
                'id': filiere.id,
                'code': filiere.code,
                'libelle': filiere.libelle,
                'message': 'Filière modifiée avec succès'
            })
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Erreur modification filière: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, pk=None):
        """Modification partielle (PATCH)"""
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        """Supprimer une filière"""
        try:
            filiere = Filiere.objects.get(id=pk)
            
            # Vérifier candidats associés
            candidats_count = Candidat.objects.filter(filiere=filiere).count()
            if candidats_count > 0:
                return Response(
                    {'error': f'Impossible de supprimer: {candidats_count} candidat(s) associé(s)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier responsable
            from authentication.models import ResponsableFiliere
            if ResponsableFiliere.objects.filter(filiere=filiere).exists():
                return Response(
                    {'error': 'Impossible de supprimer: un responsable est affecté'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            filiere_libelle = filiere.libelle
            filiere.delete()
            
            return Response({
                'message': f'Filière "{filiere_libelle}" supprimée avec succès'
            })
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'], url_path='set-capacity')
    def set_capacity(self, request, pk=None):
        """Définir la capacité d'une filière"""
        try:
            filiere = Filiere.objects.get(id=pk)
            
            if not hasattr(filiere, 'quota'):
                return Response(
                    {'error': 'Le modèle Filiere ne supporte pas les quotas'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            quota = request.data.get('quota')
            if quota is None:
                return Response(
                    {'error': 'Le quota est obligatoire'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                quota_int = int(quota)
                if quota_int < 0:
                    raise ValueError
            except ValueError:
                return Response(
                    {'error': 'Quota invalide (doit être >= 0)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            filiere.quota = quota_int
            filiere.save()
            
            return Response({
                'id': filiere.id,
                'libelle': filiere.libelle,
                'quota': filiere.quota,
                'message': 'Quota mis à jour avec succès'
            })
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """Activer/Désactiver une filière"""
        try:
            filiere = Filiere.objects.get(id=pk)
            filiere.is_active = not filiere.is_active
            filiere.save()
            
            return Response({
                'id': filiere.id,
                'libelle': filiere.libelle,
                'is_active': filiere.is_active,
                'message': f'Filière {"activée" if filiere.is_active else "désactivée"}'
            })
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='export')
    def export_candidats(self, request, pk=None):
        """Exporter les candidats d'une filière en CSV"""
        try:
            filiere = Filiere.objects.get(id=pk)
            
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="candidats_{filiere.code}_{timezone.now().date()}.csv"'
            
            writer = csv.writer(response)
            
            # En-tête
            writer.writerow([f'LISTE DES CANDIDATS - {filiere.libelle}'])
            writer.writerow(['Date d\'export', timezone.now().strftime('%d/%m/%Y %H:%M')])
            writer.writerow([])
            
            # Colonnes
            writer.writerow([
                'Matricule', 'Nom', 'Prénom', 'Email', 'Téléphone',
                'Sexe', 'Date naissance', 'Série', 'Mention', 'Statut'
            ])
            
            # Données
            candidats = Candidat.objects.filter(filiere=filiere).select_related(
                'serie', 'mention'
            ).order_by('nom', 'prenom')
            
            for candidat in candidats:
                writer.writerow([
                    candidat.matricule or 'N/A',
                    candidat.nom,
                    candidat.prenom,
                    candidat.email,
                    candidat.telephone or 'N/A',
                    candidat.sexe or 'N/A',
                    candidat.date_naissance.strftime('%d/%m/%Y') if candidat.date_naissance else 'N/A',
                    candidat.serie.libelle if candidat.serie else 'N/A',
                    candidat.mention.libelle if candidat.mention else 'N/A',
                    candidat.statut_dossier
                ])
            
            return response
            
        except Filiere.DoesNotExist:
            return Response(
                {'error': 'Filière non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ============================================
# 1. configurations/views.py - CORRIGER LES IMPORTS
# ============================================
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
import csv

from candidats.models import Region, Departement, Candidat
from authentication.permissions import IsAdminAcademique
from .models import (
    Filiere, Niveau, Diplome, CentreExamen, CentreDepot,
    Bac, Serie, Mention, SerieFiliere
)
from .serializers import (
    FiliereSerializer, NiveauSerializer, DiplomeSerializer,
    CentreExamenSerializer, CentreDepotSerializer,
    BacSerializer, SerieSerializer, MentionSerializer,
    RegionSerializer, DepartementSerializer
)


# ============================================
# FiliereViewSet (déjà bon dans ton code)
# ============================================
class FiliereViewSet(viewsets.ViewSet):
    """ViewSet pour la gestion complète des filières"""
    permission_classes = [IsAuthenticated, IsAdminAcademique]
    
    # ... (garder tout ton code du FiliereViewSet tel quel)


# ============================================
# VUES LISTES SIMPLES
# ============================================
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

class RegionListView(generics.ListAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]

class DepartementListView(generics.ListAPIView):
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer
    permission_classes = [permissions.AllowAny]


# ============================================
# FONCTIONS CASCADE
# ============================================
@api_view(['GET'])
@permission_classes([AllowAny])
def series_by_bac(request, bac_id):
    """Séries d'un BAC donné"""
    series = Serie.objects.filter(bac_id=bac_id)
    serializer = SerieSerializer(series, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def filieres_by_serie(request, serie_id):
    """Filières accessibles via une série donnée"""
    serie_filieres = SerieFiliere.objects.filter(serie_id=serie_id)
    filieres = Filiere.objects.filter(
        id__in=serie_filieres.values_list('filiere_id', flat=True)
    ).filter(is_active=True).distinct()
    
    serializer = FiliereSerializer(filieres, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def niveaux_by_serie_filiere(request, serie_id, filiere_id):
    """Niveaux pour une série et filière données"""
    serie_filieres = SerieFiliere.objects.filter(serie_id=serie_id, filiere_id=filiere_id)
    niveaux = Niveau.objects.filter(series_filieres__in=serie_filieres).distinct().order_by('ordre')
    serializer = NiveauSerializer(niveaux, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def diplomes_by_niveau_filiere(request, niveau_id, filiere_id):
    """Diplômes pour un niveau et filière donnés"""
    diplomes = Diplome.objects.filter(
        filieres__filiere_id=filiere_id,
        filieres__niveau_id=niveau_id
    ).distinct()
    serializer = DiplomeSerializer(diplomes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def mentions_by_bac(request, bac_id):
    """Mentions d'un BAC donné"""
    mentions = Mention.objects.filter(bac_id=bac_id, is_active=True)
    serializer = MentionSerializer(mentions, many=True)
    return Response(serializer.data)


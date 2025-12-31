from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import CandidatEnrollementSerializer
from .models import Candidat
from authentication.models import CodeQuitus
from django.utils import timezone
import json

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def enrollement_view(request):
    """Compléter profil candidat - USER AUTHENTIFIÉ"""
    
    user = request.user
    print(f"\n{'='*80}")
    print(f"👤 USER AUTHENTIFIÉ: {user.email} (role: {user.role})")
    print(f"{'='*80}")
    
    # ✅ 1. VÉRIFIER RÔLE
    if user.role != 'candidat':
        print("❌ User n'est pas candidat")
        return Response({
            'error': 'Accès refusé',
            'message': 'Seuls les candidats peuvent accéder à cette fonctionnalité.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # ✅ 2. LOG STATUT ACTUEL
    try:
        candidat_existant = Candidat.objects.get(user=user)
        print(f"📋 Candidat existant: {candidat_existant.matricule} | Statut: {candidat_existant.statut_dossier}")
    except Candidat.DoesNotExist:
        print("📋 Aucun candidat trouvé")
    
    # ✅ 3. DEBUG FICHIERS (CRITIQUE)
    print(f"\n📂 FICHIERS REÇUS ({len(request.FILES)}):")
    for key in request.FILES.keys():
        file = request.FILES[key]
        print(f"  ✅ {key}: {file.name} ({file.size} bytes)")
    
    print(f"\n📥 DONNÉES ({len(request.data)}):")
    for key, value in request.data.items():
        print(f"  📝 {key}: {value}")
    
    # 🔥 FIX : COMBINER request.data + request.FILES
    data = request.data.copy()  # Copie mutable
    for key, file in request.FILES.items():
        data[key] = file  # Ajoute les fichiers !
    
    print(f"\n🔗 DATA+FICHIERS ({len(data)} champs):")
    for key in data.keys():
        print(f"  ✅ {key}: {'FILE' if hasattr(data[key], 'name') else data[key]}")
    
    # ✅ 4. VALIDATION SERIALIZER
    serializer = CandidatEnrollementSerializer(data=data, context={'request': request})
    
    print(f"\n🔍 VALIDATION...")
    if serializer.is_valid():
        print("✅ VALIDATION OK")
        
        try:
            print(f"\n💾 SAUVEGARDE...")
            candidat = serializer.save()
            print(f"✅ SUCCÈS: {candidat.matricule} | Statut: {candidat.statut_dossier}")
            
            return Response({
                'success': True,
                'message': 'Enrôlement réussi ! Votre dossier est complet.',
                'candidat': {
                    'matricule': candidat.matricule,
                    'nom_complet': f'{candidat.nom} {candidat.prenom}',
                    'statut_dossier': candidat.statut_dossier,
                },
                'next_steps': [
                    'Votre dossier a été soumis avec succès',
                    'Consultez votre tableau de bord pour suivre l\'état'
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ ERREUR SAUVEGARDE: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Erreur sauvegarde',
                'message': str(e),
                'support': 'support@estlc.cm'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ❌ ERREURS
    print(f"❌ ERREURS: {serializer.errors}")
    return Response({
        'error': 'Données invalides',
        'details': serializer.errors,
        'message': 'Veuillez corriger les erreurs indiquées.'
    }, status=status.HTTP_400_BAD_REQUEST)

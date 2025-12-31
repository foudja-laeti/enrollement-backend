# authentication/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .serializers import (
    LoginSerializer, UserSerializer, RegisterSerializer,
    CreateAdminUserSerializer, UpdateUserSerializer, ResetPasswordSerializer
)
from .models import CodeQuitus, User, UserActionLog
from .permissions import IsSuperAdmin, IsAdminAcademique, IsResponsableFiliere

def get_tokens_for_user(user):
    """Générer les tokens JWT pour un utilisateur"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_client_ip(request):
    """Récupérer l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ==========================================
# AUTHENTIFICATION (PUBLIC)
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_quitus_view(request):
    """
    Vérifier un code quitus.
    - Si non utilisé -> status: "available"
    - Si utilisé par l'utilisateur connecté -> status: "owned"
    - Si utilisé par un autre -> error
    """
    code_quitus = request.data.get('code_quitus')
    
    if not code_quitus:
        return Response({'error': 'Code quitus requis'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        quitus = CodeQuitus.objects.get(code=code_quitus)
    except CodeQuitus.DoesNotExist:
        return Response({'error': 'Code quitus invalide'}, status=status.HTTP_404_NOT_FOUND)
    
    if not quitus.est_valide() and not quitus.utilise:
        return Response({'error': 'Code quitus expiré'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not quitus.utilise:
        return Response({
            'status': 'available',
            'message': 'Code quitus valide et disponible',
            'montant': str(quitus.montant),
            'reference_bancaire': quitus.reference_bancaire,
            'date_expiration': quitus.date_expiration.isoformat(),
        }, status=status.HTTP_200_OK)

    user = request.user if request.user.is_authenticated else None
    
    if not user:
        return Response({
            'error': 'Ce code est déjà utilisé. Veuillez vous connecter si c\'est votre code.',
            'action': 'login_required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if quitus.utilisateur_id == user.id:
        return Response({
            'status': 'owned',
            'message': 'Ce code est déjà associé à votre compte',
            'montant': str(quitus.montant),
            'reference_bancaire': quitus.reference_bancaire,
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Ce code quitus est déjà utilisé par un autre candidat'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Connexion utilisateur"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'Connexion réussie',
            'user': user_data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Inscription candidat avec code quitus"""
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        return Response({
            'message': 'Inscription réussie',
            'user': user_data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Déconnexion (blacklist du refresh token)"""
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Récupérer le profil de l'utilisateur connecté"""
    user_data = UserSerializer(request.user).data
    return Response(user_data, status=status.HTTP_200_OK)


# ==========================================
# GESTION DES UTILISATEURS (ADMIN)
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users_view(request):
    """
    Liste des utilisateurs selon le rôle :
    - super_admin : Voit admin_academique, responsable_filiere, candidats
    - admin_academique : Voit responsable_filiere, candidats
    - responsable_filiere : Voit candidats de sa filière
    """
    user = request.user
    
    if user.role == 'super_admin':
        users = User.objects.filter(
            role__in=['admin_academique', 'responsable_filiere', 'candidat']
        ).select_related('created_by')
    elif user.role == 'admin_academique':
        users = User.objects.filter(
            role__in=['responsable_filiere', 'candidat']
        ).select_related('created_by')
    elif user.role == 'responsable_filiere':
        # Voir seulement les candidats de sa filière
        if hasattr(user, 'responsable_filiere_profile') and user.responsable_filiere_profile.filiere:
            filiere_id = user.responsable_filiere_profile.filiere.id
            users = User.objects.filter(
                role='candidat',
                candidat__filiere_id=filiere_id
            ).select_related('created_by')
        else:
            users = User.objects.none()
    else:
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    # Filtres
    role_filter = request.query_params.get('role')
    search = request.query_params.get('search')
    is_active = request.query_params.get('is_active')
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(nom__icontains=search) |
            Q(prenom__icontains=search)
        )
    
    if is_active is not None:
        users = users.filter(is_active=is_active.lower() == 'true')
    
    serializer = UserSerializer(users, many=True)
    return Response({
        'count': users.count(),
        'users': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_view(request, user_id):
    """Récupérer les détails d'un utilisateur"""
    target_user = get_object_or_404(User, id=user_id)
    
    if not request.user.can_manage_user(target_user):
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = UserSerializer(target_user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_admin_user_view(request):
    """
    Créer un utilisateur admin
    - super_admin peut créer : admin_academique, responsable_filiere
    - admin_academique peut créer : responsable_filiere
    """
    if request.user.role not in ['super_admin', 'admin_academique']:
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = CreateAdminUserSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = serializer.save()
        user_data = UserSerializer(user).data
        return Response({
            'message': 'Utilisateur créé avec succès',
            'user': user_data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_view(request, user_id):
    """Modifier un utilisateur"""
    target_user = get_object_or_404(User, id=user_id)
    
    serializer = UpdateUserSerializer(
        target_user,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = serializer.save()
        user_data = UserSerializer(user).data
        return Response({
            'message': 'Utilisateur modifié avec succès',
            'user': user_data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_active_view(request, user_id):
    """Activer/Désactiver un compte utilisateur"""
    target_user = get_object_or_404(User, id=user_id)
    
    if not request.user.can_manage_user(target_user):
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    target_user.is_active = not target_user.is_active
    target_user.save()
    
    # Log l'action
    UserActionLog.objects.create(
        actor=request.user,
        target_user=target_user,
        action='toggle_active',
        details={
            'is_active': target_user.is_active,
            'email': target_user.email
        },
        ip_address=get_client_ip(request)
    )
    
    return Response({
        'message': f"Compte {'activé' if target_user.is_active else 'désactivé'}",
        'is_active': target_user.is_active
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_user_password_view(request, user_id):
    """Réinitialiser le mot de passe d'un utilisateur"""
    target_user = get_object_or_404(User, id=user_id)
    
    serializer = ResetPasswordSerializer(
        data=request.data,
        context={
            'request': request,
            'target_user': target_user
        }
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Mot de passe réinitialisé avec succès'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_view(request, user_id):
    """
    Supprimer un utilisateur
    Nécessite confirmation + raison
    """
    target_user = get_object_or_404(User, id=user_id)
    
    if not request.user.can_manage_user(target_user):
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    # Vérifier la confirmation
    confirmation = request.data.get('confirmation')
    raison = request.data.get('raison', '')
    
    if confirmation != target_user.email:
        return Response({
            'error': 'Confirmation invalide. Veuillez saisir l\'email de l\'utilisateur.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Archiver avant suppression
    UserActionLog.objects.create(
        actor=request.user,
        target_user=target_user,
        action='delete_user',
        details={
            'email': target_user.email,
            'nom': target_user.nom,
            'prenom': target_user.prenom,
            'role': target_user.role,
            'raison': raison
        },
        ip_address=get_client_ip(request)
    )
    
    user_email = target_user.email
    target_user.delete()
    
    return Response({
        'message': f'Utilisateur {user_email} supprimé avec succès'
    }, status=status.HTTP_200_OK)


# ==========================================
# STATISTIQUES
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_statistics_view(request):
    """
    Statistiques selon le rôle :
    - super_admin : Tous les utilisateurs + candidats
    - admin_academique : Responsables filière + candidats
    - responsable_filiere : Candidats de sa filière
    """
    user = request.user
    
    stats = {}
    
    if user.role == 'super_admin':
        stats = {
            'total_admin_academique': User.objects.filter(role='admin_academique').count(),
            'total_responsable_filiere': User.objects.filter(role='responsable_filiere').count(),
            'total_candidats': User.objects.filter(role='candidat').count(),
            'candidats_actifs': User.objects.filter(role='candidat', is_active=True).count(),
            'total_enrollements': User.objects.filter(role='candidat', candidat__isnull=False).count(),
            'codes_quitus_utilises': CodeQuitus.objects.filter(utilise=True).count(),
            'codes_quitus_disponibles': CodeQuitus.objects.filter(utilise=False).count(),
        }
    
    elif user.role == 'admin_academique':
        stats = {
            'total_responsable_filiere': User.objects.filter(role='responsable_filiere').count(),
            'total_candidats': User.objects.filter(role='candidat').count(),
            'candidats_actifs': User.objects.filter(role='candidat', is_active=True).count(),
            'total_enrollements': User.objects.filter(role='candidat', candidat__isnull=False).count(),
        }
    
    elif user.role == 'responsable_filiere':
        if hasattr(user, 'responsable_filiere_profile') and user.responsable_filiere_profile.filiere:
            filiere_id = user.responsable_filiere_profile.filiere.id
            stats = {
                'total_candidats': User.objects.filter(
                    role='candidat',
                    candidat__filiere_id=filiere_id
                ).count(),
                'candidats_actifs': User.objects.filter(
                    role='candidat',
                    is_active=True,
                    candidat__filiere_id=filiere_id
                ).count(),
                'enrollements_en_attente': User.objects.filter(
                    role='candidat',
                    candidat__filiere_id=filiere_id,
                    candidat__statut_dossier='en_attente'
                ).count(),
            }
        else:
            stats = {}
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_action_logs_view(request):
    """Récupérer les logs d'actions (audit)"""
    if request.user.role not in ['super_admin', 'admin_academique']:
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    logs = UserActionLog.objects.all()
    
    # Filtres
    action_filter = request.query_params.get('action')
    user_id = request.query_params.get('user_id')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_id:
        logs = logs.filter(Q(actor_id=user_id) | Q(target_user_id=user_id))
    
    logs = logs.select_related('actor', 'target_user')[:100]  # Limite 100
    
    data = [{
        'id': log.id,
        'actor': log.actor.get_full_name() if log.actor else 'Système',
        'target_user': log.target_user.get_full_name() if log.target_user else None,
        'action': log.get_action_display(),
        'details': log.details,
        'created_at': log.created_at.isoformat()
    } for log in logs]
    
    return Response({
        'count': len(data),
        'logs': data
    }, status=status.HTTP_200_OK)
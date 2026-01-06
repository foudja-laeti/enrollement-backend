# authentication/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password  # ✅ Ajouté
from django.core.exceptions import ValidationError 
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
    user = request.user
    
    print(f"🔍 DEBUG - Utilisateur: {user.email} (rôle: {user.role})")
    
    if user.role == 'super_admin':
        users = User.objects.filter(
            role__in=['admin_academique', 'responsable_filiere', 'candidat']
        ).select_related('candidat', 'created_by')
        print(f"🔍 Super Admin → {users.count()} users")
        
    elif user.role == 'admin_academique':
        users = User.objects.filter(
            role__in=['responsable_filiere', 'candidat']
        ).select_related('candidat', 'created_by')
    elif user.role == 'responsable_filiere':
        if hasattr(user, 'responsable_filiere_profile') and user.responsable_filiere_profile.filiere:
            filiere_id = user.responsable_filiere_profile.filiere.id
            users = User.objects.filter(
                role='candidat', candidat__filiere_id=filiere_id
            ).select_related('created_by')
        else:
            users = User.objects.none()
    else:
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    # ✅ FIX CRITIQUE : Vérifie is_active NON VIDE
    is_active = request.query_params.get('is_active')
    if is_active and is_active.lower() in ['true', 'false']:  # ← FIX !
        users = users.filter(is_active=(is_active.lower() == 'true'))
        print(f"🔍 Filtre actif: {is_active}")
    else:
        print("🔍 Pas de filtre actif")
    
    # Autres filtres
    role_filter = request.query_params.get('role')
    search = request.query_params.get('search')
    
    if role_filter:
        users = users.filter(role=role_filter)
        print(f"🔍 Filtre rôle: {role_filter}")
    if search:
        users = users.filter(
            Q(email__icontains=search) | Q(nom__icontains=search) | Q(prenom__icontains=search)
        )
        print(f"🔍 Recherche: {search}")
    
    final_count = users.count()
    print(f"✅ FINAL: {final_count} utilisateurs")
    
    serializer = UserSerializer(users, many=True)
    return Response({
        'count': final_count,
        'users': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_view(request, pk):  # ← pk obligatoire !
    """
    MODIFIER utilisateur (super_admin seulement)
    """
    user = request.user
    
    if user.role != 'super_admin':
        return Response({'error': 'Super admin requis'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        target_user = User.objects.get(id=pk)
    except User.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserSerializer(target_user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        print(f"✅ User {pk} modifié par {user.email}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_active_view(request, pk):
    """
    Toggle actif/inactif utilisateur
    """
    user = request.user
    
    if user.role != 'super_admin':
        return Response({'error': 'Super admin requis'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        target_user = User.objects.get(id=pk)
        target_user.is_active = not target_user.is_active
        target_user.save()
        print(f"✅ User {pk} {'activé' if target_user.is_active else 'désactivé'} par {user.email}")
        return Response({
            'id': pk,
            'is_active': target_user.is_active,
            'message': 'Statut mis à jour'
        })
    except User.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

# Remplace ta fonction delete_user_view par celle-ci :

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_view(request, pk):  # ← AJOUTE pk ici !
    """
    SUPPRIMER un utilisateur (super_admin seulement)
    URL: DELETE /api/auth/users/delete/<pk>/
    """
    user = request.user
    
    # Vérification permission
    if user.role != 'super_admin':
        return Response(
            {'error': 'Super admin requis'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer l'utilisateur cible
    try:
        target_user = User.objects.get(id=pk)
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier la confirmation par email
    confirmation = request.data.get('confirmation')
    if not confirmation or confirmation != target_user.email:
        return Response(
            {'error': f'Confirmez avec l\'email exact: {target_user.email}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Empêcher la suppression de soi-même
    if target_user.id == user.id:
        return Response(
            {'error': 'Vous ne pouvez pas supprimer votre propre compte'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Log avant suppression
    UserActionLog.objects.create(
        actor=user,
        target_user=target_user,
        action='delete_user',
        details={
            'email': target_user.email,
            'nom': target_user.nom,
            'prenom': target_user.prenom,
            'role': target_user.role
        },
        ip_address=get_client_ip(request)
    )
    
    # Suppression
    target_user.delete()
    
    print(f"✅ User {pk} ({target_user.email}) supprimé par {user.email}")
    
    return Response({
        'success': True,
        'message': 'Utilisateur supprimé avec succès'
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


# Dans authentication/views.py, remplacer create_admin_user_view

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_admin_user_view(request):
    """
    Créer un utilisateur admin (unifié pour tous les rôles)
    - super_admin peut créer : admin_academique, responsable_filiere
    - admin_academique peut créer : responsable_filiere
    """
    user = request.user
    
    print(f"🔍 CREATE USER - Acteur: {user.email} (rôle: {user.role})")
    print(f"📦 Data reçue: {request.data}")
    
    if user.role not in ['super_admin', 'admin_academique']:
        return Response(
            {'error': 'Accès refusé'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer le rôle demandé
    target_role = request.data.get('role')
    
    # Vérifier les permissions selon la hiérarchie
    if user.role == 'super_admin':
        allowed_roles = ['admin_academique', 'responsable_filiere']
    elif user.role == 'admin_academique':
        allowed_roles = ['responsable_filiere']
    else:
        allowed_roles = []
    
    if target_role not in allowed_roles:
        return Response({
            'error': f'Vous ne pouvez pas créer un utilisateur avec le rôle {target_role}'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Validation des données
    required_fields = ['nom', 'prenom', 'email', 'role']
    for field in required_fields:
        if not request.data.get(field):
            return Response({
                'error': f'Le champ {field} est requis'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Si responsable_filiere, filiere_id obligatoire
    if target_role == 'responsable_filiere' and not request.data.get('filiere_id'):
        return Response({
            'error': 'Le champ filiere_id est obligatoire pour un responsable de filière'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Vérifier si l'email existe déjà
    if User.objects.filter(email=request.data['email']).exists():
        return Response({
            'error': 'Cet email est déjà utilisé'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Générer un mot de passe automatique
            password = User.objects.make_random_password(length=12)
            
            # Créer l'utilisateur
            new_user = User.objects.create_user(
                email=request.data['email'],
                password=password,
                nom=request.data['nom'],
                prenom=request.data['prenom'],
                role=target_role,
                created_by=user,
                is_staff=True,
                is_email_verified=True
            )
            
            print(f"✅ User créé: {new_user.email} (ID: {new_user.id})")
            
            # Si responsable de filière, créer le profil
            if target_role == 'responsable_filiere':
                from configurations.models import Filiere
                filiere_id = request.data.get('filiere_id')
                
                try:
                    filiere = Filiere.objects.get(id=filiere_id)
                    ResponsableFiliere.objects.create(
                        user=new_user,
                        filiere=filiere,
                        telephone=request.data.get('telephone', '')
                    )
                    print(f"✅ Profil Responsable Filière créé pour filière: {filiere.libelle}")
                except Filiere.DoesNotExist:
                    raise Exception(f"Filière ID {filiere_id} non trouvée")
            
            # Log l'action
            UserActionLog.objects.create(
                actor=user,
                target_user=new_user,
                action='create_user',
                details={
                    'role': target_role,
                    'email': new_user.email,
                    'password_preview': password[:4] + '***'
                },
                ip_address=get_client_ip(request)
            )
            
            user_data = UserSerializer(new_user).data
            
            return Response({
                'success': True,
                'message': f'Utilisateur créé avec succès',
                'user': user_data,
                'password_temporaire': password  # ⚠️ À afficher une seule fois
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        print(f"❌ Erreur création: {str(e)}")
        return Response({
            'error': f'Erreur lors de la création: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evolution_candidats_view(request):
    """ÉVOLUTION candidats derniers 6 mois"""
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    from datetime import datetime, timedelta
    
    user = request.user
    if user.role != 'super_admin':
        return Response({'error': 'Super admin requis'}, status=status.HTTP_403_FORBIDDEN)
    
    # Derniers 6 mois
    end_date = datetime.now()
    months = []
    data = []
    
    for i in range(6):
        month_date = end_date - timedelta(days=30*i)
        month_str = month_date.strftime('%b %y')
        
        count = User.objects.filter(
            role='candidat',
            date_joined__month=month_date.month,
            date_joined__year=month_date.year,
            is_active=True
        ).count()
        
        months.append(month_str)
        data.append(count)
    
    return Response({
        'evolution': data,
        'labels': months[::-1],  # Ordre chronologique
        'croissance': ((data[-1] - data[0]) / data[0] * 100) if data[0] > 0 else 0
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_active_view(request, pk):  # ← pk déjà OK
    """
    Toggle actif/inactif utilisateur
    URL: POST /api/auth/users/<pk>/toggle-active/
    """
    user = request.user
    
    if user.role != 'super_admin':
        return Response(
            {'error': 'Super admin requis'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        target_user = User.objects.get(id=pk)
        
        # Empêcher de se désactiver soi-même
        if target_user.id == user.id:
            return Response(
                {'error': 'Vous ne pouvez pas désactiver votre propre compte'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Toggle
        target_user.is_active = not target_user.is_active
        target_user.save()
        
        # Log
        UserActionLog.objects.create(
            actor=user,
            target_user=target_user,
            action='toggle_active',
            details={
                'is_active': target_user.is_active,
                'email': target_user.email
            },
            ip_address=get_client_ip(request)
        )
        
        print(f"✅ User {pk} {'activé' if target_user.is_active else 'désactivé'} par {user.email}")
        
        return Response({
            'success': True,
            'id': pk,
            'is_active': target_user.is_active,
            'message': f"Compte {'activé' if target_user.is_active else 'désactivé'} avec succès"
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_user_password_view(request, pk):  # ← pk au lieu de user_id
    """
    Réinitialiser le mot de passe d'un utilisateur
    URL: POST /api/auth/users/<pk>/reset-password/
    """
    user = request.user
    
    if user.role != 'super_admin':
        return Response(
            {'error': 'Super admin requis'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        target_user = User.objects.get(id=pk)
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Générer nouveau mot de passe
    new_password = request.data.get('new_password')
    if not new_password:
        # Si pas fourni, générer automatiquement
        new_password = User.objects.make_random_password(length=12)
    
    # Valider le mot de passe (minimum 8 caractères)
    if len(new_password) < 8:
        return Response(
            {'error': 'Le mot de passe doit contenir au moins 8 caractères'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Réinitialiser
    target_user.set_password(new_password)
    target_user.save()
    
    # Log
    UserActionLog.objects.create(
        actor=user,
        target_user=target_user,
        action='reset_password',
        details={
            'email': target_user.email,
            'password_preview': new_password[:4] + '***'
        },
        ip_address=get_client_ip(request)
    )
    
    print(f"✅ Mot de passe réinitialisé pour user {pk} par {user.email}")
    
    return Response({
        'success': True,
        'message': 'Mot de passe réinitialisé avec succès',
        'new_password': new_password  # ⚠️ À transmettre une seule fois !
    }, status=status.HTTP_200_OK)

# ==========================================
# STATISTIQUES
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_statistics_view(request):
    user = request.user
    stats = {}
    
    # Codes Quitus pour TOUS les rôles
    codes_quitus = {
        'codes_quitus_total': CodeQuitus.objects.count(),
        'codes_quitus_disponibles': CodeQuitus.objects.filter(utilise=False).count(),
        'codes_quitus_utilises': CodeQuitus.objects.filter(utilise=True).count(),
    }
    
    if user.role == 'super_admin':
        stats = {
            'total_admin_academique': User.objects.filter(role='admin_academique').count(),
            'total_responsable_filiere': User.objects.filter(role='responsable_filiere').count(),
            'total_candidats': User.objects.filter(role='candidat').count(),
            'candidats_actifs': User.objects.filter(role='candidat', is_active=True).count(),
            'total_enrollements': User.objects.filter(role='candidat', candidat__isnull=False).count(),
            **codes_quitus  # ← CORRECT : à la fin
        }
    
    elif user.role == 'admin_academique':
        stats = {
            'total_responsable_filiere': User.objects.filter(role='responsable_filiere').count(),
            'total_candidats': User.objects.filter(role='candidat').count(),
            'candidats_actifs': User.objects.filter(role='candidat', is_active=True).count(),
            'total_enrollements': User.objects.filter(role='candidat', candidat__isnull=False).count(),
              # ← AJOUTE ÇA :
        'candidats': {
            'par_statut': list(Candidat.objects
                .values('statut_dossier')
                .annotate(count=Count('statut_dossier'))
                .order_by('-count')
            )
        },
    
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

# ==========================================
# CRÉATION SPÉCIALISÉE (Super Admin → Admin Acad → Resp Filière)
# ==========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_admin_user_view(request):
    """
    ✅ ENDPOINT UNIFIÉ pour créer Admin Académique ET Responsable Filière
    URL: POST /api/auth/users/create/
    """
    print(f"🔍 CREATE USER - Acteur: {request.user.email} (rôle: {request.user.role})")
    print(f"📦 Data reçue: {request.data}")
    
    # Vérifier les permissions
    if not request.user.role in ['super_admin', 'admin_academique']:
        return Response(
            {'error': 'Permission refusée'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CreateAdminUserSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            
            return Response({
                'success': True,
                'user': UserSerializer(user).data,
                'message': f'{serializer.validated_data["role"]} créé avec succès'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ Erreur création user: {str(e)}")
            return Response(
                {'error': f'Erreur lors de la création: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    print(f"❌ Erreurs validation: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_filieres_view(request):
    """Liste filières pour sélection Resp. Filière"""
    from configurations.models import Filiere
    
    try:
        # ✅ Utilise 'libelle' au lieu de 'nom'
        filieres = Filiere.objects.filter(is_active=True).values('id', 'libelle', 'code')
        
        # Mapping pour le frontend
        filieres_list = [
            {
                'id': f['id'],
                'nom': f['libelle'],  # libelle -> nom
                'code': f['code']
            }
            for f in filieres
        ]
        
        return Response({
            'filieres': filieres_list,
            'count': len(filieres_list)
        })
    except Exception as e:
        print(f"❌ Erreur filières: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_responsable_filiere_view(request):
    """Super Admin + Admin Acad → Créer Resp. Filière"""
    user = request.user
    
    print(f"🔍 CREATE USER - Acteur: {user.email} (rôle: {user.role})")
    print(f"📦 Data reçue: {request.data}")
    
    # Vérification des permissions
    if user.role not in ['super_admin', 'admin_academique']:
        return Response(
            {'error': 'Accès refusé. Seuls les Super Admin et Admin Académiques peuvent créer des responsables de filière.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CreateResponsableFiliereSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            # Générer mot de passe si non fourni
            password = request.data.get('password')
            if not password:
                password = User.objects.make_random_password(length=12)
            
            # Créer l'utilisateur (le serializer gère le mot de passe)
            user_new = serializer.save()
            
            print(f"✅ User créé: {user_new.email} - Filière: {user_new.responsable_filiere_profile.filiere}")
            
            # Log de l'action
            UserActionLog.objects.create(
                actor=request.user,
                target_user=user_new,
                action='create_user',
                details={
                    'role': 'responsable_filiere',
                    'filiere_id': request.data.get('filiere_id'),
                    'filiere_nom': user_new.responsable_filiere_profile.filiere.libelle if user_new.responsable_filiere_profile.filiere else 'N/A',
                    'password_fourni': bool(request.data.get('password'))
                }
            )
            
            # Préparer la réponse
            response_data = {
                'success': True,
                'user': UserSerializer(user_new).data,
                'message': 'Responsable de Filière créé avec succès'
            }
            
            # Inclure le mot de passe temporaire seulement si généré automatiquement
            if not request.data.get('password'):
                response_data['password_temporaire'] = password
                response_data['message'] += '. Mot de passe temporaire généré.'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ Erreur création user: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Nettoyer si l'utilisateur a été créé mais pas le profil
            if 'user_new' in locals():
                user_new.delete()
            
            return Response(
                {'error': f'Erreur lors de la création: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    print(f"❌ Erreurs validation: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PATCH', 'PUT'])  # ✅ Accepte GET, PATCH et PUT
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    GET: Récupérer le profil de l'utilisateur connecté
    PATCH/PUT: Mettre à jour le profil
    """
    user = request.user
    
    if request.method == 'GET':
        # Récupérer le profil avec téléphone
        profile_data = {
            'id': user.id,
            'email': user.email,
            'nom': user.nom,
            'prenom': user.prenom,
            'role': user.role,
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'created_at': user.created_at,
        }
        
        # Ajouter le téléphone selon le rôle
        if user.role == 'responsable_filiere' and hasattr(user, 'responsable_filiere_profile'):
            profile_data['telephone'] = user.responsable_filiere_profile.telephone
        elif user.role == 'candidat' and hasattr(user, 'candidat'):
            profile_data['telephone'] = user.candidat.telephone
        
        return Response(profile_data)
    
    elif request.method in ['PATCH', 'PUT']:
        # Mettre à jour le profil
        data = request.data
        
        # Champs modifiables
        if 'nom' in data:
            user.nom = data['nom']
        if 'prenom' in data:
            user.prenom = data['prenom']
        
        # Email : vérifier qu'il n'est pas déjà utilisé
        if 'email' in data and data['email'] != user.email:
            from authentication.models import User
            if User.objects.filter(email=data['email']).exists():
                return Response(
                    {'error': 'Cet email est déjà utilisé'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.email = data['email']
            user.is_email_verified = False  # Nécessite re-vérification
        
        user.save()
        
        return Response({
            'success': True,
            'message': 'Profil mis à jour avec succès',
            'user': {
                'id': user.id,
                'email': user.email,
                'nom': user.nom,
                'prenom': user.prenom,
                'role': user.role,
            }
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    POST: Changer le mot de passe de l'utilisateur connecté
    Body: {
        "current_password": "ancien_mot_de_passe",
        "new_password": "nouveau_mot_de_passe",
        "confirm_password": "nouveau_mot_de_passe"
    }
    """
    user = request.user
    data = request.data
    
    # ✅ Debug : afficher les données reçues
    print(f"🔐 Change password - User: {user.email}")
    print(f"📦 Data reçue: {data.keys()}")
    
    # Vérifier que tous les champs sont présents
    required_fields = ['current_password', 'new_password', 'confirm_password']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        print(f"❌ Champs manquants: {missing_fields}")
        return Response(
            {'error': f'Champs manquants: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    current_password = data['current_password']
    new_password = data['new_password']
    confirm_password = data['confirm_password']
    
    # Vérifier l'ancien mot de passe
    if not user.check_password(current_password):
        return Response(
            {'error': 'Mot de passe actuel incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier que les nouveaux mots de passe correspondent
    if new_password != confirm_password:
        return Response(
            {'error': 'Les nouveaux mots de passe ne correspondent pas'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier que le nouveau mot de passe est différent de l'ancien
    if current_password == new_password:
        return Response(
            {'error': 'Le nouveau mot de passe doit être différent de l\'ancien'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Valider le nouveau mot de passe
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response(
            {'error': list(e.messages)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Changer le mot de passe
    user.set_password(new_password)
    user.save()
    
    # Logger l'action
    from authentication.models import UserActionLog
    UserActionLog.objects.create(
        actor=user,
        target_user=user,
        action='change_password',
        details={'message': 'Utilisateur a changé son propre mot de passe'},
        ip_address=request.META.get('REMOTE_ADDR', '')
    )
    
    return Response({
        'success': True,
        'message': 'Mot de passe changé avec succès'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """
    POST: Mettre à jour le profil étendu (téléphone, adresse, etc.)
    """
    user = request.user
    data = request.data
    
    # Pour les candidats
    if user.role == 'candidat' and hasattr(user, 'candidat'):
        candidat = user.candidat
        
        # Mettre à jour les informations du candidat
        if 'telephone' in data:
            candidat.telephone = data['telephone']
        if 'telephone_secondaire' in data:
            candidat.telephone_secondaire = data['telephone_secondaire']
        if 'adresse_actuelle' in data:
            candidat.adresse_actuelle = data['adresse_actuelle']
        if 'ville' in data:
            candidat.ville = data['ville']
        if 'quartier' in data:
            candidat.quartier = data['quartier']
        
        candidat.save()
        
        return Response({
            'success': True,
            'message': 'Profil mis à jour avec succès',
            'candidat': {
                'telephone': candidat.telephone,
                'telephone_secondaire': candidat.telephone_secondaire,
                'adresse_actuelle': candidat.adresse_actuelle,
                'ville': candidat.ville,
                'quartier': candidat.quartier,
            }
        })
    
    # Pour les responsables de filière
    elif user.role == 'responsable_filiere' and hasattr(user, 'responsable_filiere_profile'):
        rf_profile = user.responsable_filiere_profile
        
        if 'telephone' in data:
            rf_profile.telephone = data['telephone']
        
        rf_profile.save()
        
        return Response({
            'success': True,
            'message': 'Profil mis à jour avec succès',
            'responsable': {
                'telephone': rf_profile.telephone,
            }
        })
    
    return Response(
        {'error': 'Type d\'utilisateur non pris en charge'},
        status=status.HTTP_400_BAD_REQUEST
    )

# authentication/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.db import transaction
from .models import CodeQuitus, ResponsableFiliere, UserActionLog
from candidats.models import Candidat

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    code_quitus = serializers.CharField(max_length=6, required=False, allow_blank=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        code_quitus = data.get('code_quitus', '').strip()

        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        
        # Les admins n'ont pas besoin de code quitus
        if user.role in ['super_admin', 'admin_academique', 'responsable_filiere']:
            data['user'] = user
            return data
        
        # Candidats : code quitus optionnel pour la connexion
        if user.role == 'candidat':
            try:
                candidat = Candidat.objects.get(user=user)
            except Candidat.DoesNotExist:
                pass
            
            if code_quitus:
                try:
                    quitus = CodeQuitus.objects.get(utilisateur=user)
                    if quitus.code != code_quitus:
                        raise serializers.ValidationError({
                            "code_quitus": "Code quitus incorrect."
                        })
                except CodeQuitus.DoesNotExist:
                    raise serializers.ValidationError({
                        "code_quitus": "Aucun quitus associé à ce compte."
                    })
        
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    candidat = serializers.SerializerMethodField()
    responsable_filiere = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'nom', 'prenom', 'role', 'is_active', 
            'is_email_verified', 'created_at', 'created_by', 'created_by_name',
            'candidat', 'responsable_filiere'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_candidat(self, obj):
        if obj.role == 'candidat' and hasattr(obj, 'candidat'):
            return {
                'id': obj.candidat.id,
                'matricule': obj.candidat.matricule,
                'nom': obj.candidat.nom,
                'prenom': obj.candidat.prenom,
                'statut_dossier': obj.candidat.statut_dossier
            }
        return None
    
    def get_responsable_filiere(self, obj):
        if obj.role == 'responsable_filiere' and hasattr(obj, 'responsable_filiere_profile'):
            profile = obj.responsable_filiere_profile
            return {
                'id': profile.id,
                'filiere': profile.filiere.nom if profile.filiere else None,
                'telephone': profile.telephone
            }
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


class RegisterSerializer(serializers.Serializer):
    """Inscription d'un nouveau candidat - VALIDATION STRICTE"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    code_quitus = serializers.CharField(max_length=6)
    
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    date_naissance = serializers.DateField()
    lieu_naissance = serializers.CharField(max_length=255)
    sexe = serializers.ChoiceField(choices=[('M', 'Masculin'), ('F', 'Féminin')])
    telephone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate_code_quitus(self, value):
        code = value.strip()
        if len(code) != 6 or not code.isdigit():
            raise serializers.ValidationError("Code quitus invalide (6 chiffres requis).")
        
        try:
            quitus = CodeQuitus.objects.select_related('utilisateur').get(code=code)
            
            if quitus.utilise:
                if quitus.utilisateur:
                    raise serializers.ValidationError(
                        f"Ce code quitus est déjà utilisé par {quitus.utilisateur.email}."
                    )
                else:
                    raise serializers.ValidationError("Ce code quitus a déjà été utilisé.")
            
            if quitus.date_expiration < timezone.now():
                raise serializers.ValidationError(
                    f"Code quitus expiré le {quitus.date_expiration.date()}."
                )
            
            self.context['code_quitus_obj'] = quitus
            
        except CodeQuitus.DoesNotExist:
            raise serializers.ValidationError(f"Le code quitus '{code}' n'existe pas.")
        
        return code

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return data

    def create(self, validated_data):
        code_quitus_obj = self.context.get('code_quitus_obj')
        if not code_quitus_obj:
            raise serializers.ValidationError("Code quitus invalide (erreur interne).")
        
        quitus_fresh = CodeQuitus.objects.get(code=code_quitus_obj.code)
        if quitus_fresh.utilise:
            raise serializers.ValidationError("Code quitus déjà utilisé.")
        if quitus_fresh.date_expiration < timezone.now():
            raise serializers.ValidationError("Code quitus expiré.")
        
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                nom=validated_data['nom'],
                prenom=validated_data['prenom'],
                role='candidat'
            )
            
            candidat = Candidat.objects.create(
                user=user,
                nom=validated_data['nom'],
                prenom=validated_data['prenom'],
                date_naissance=validated_data['date_naissance'],
                lieu_naissance=validated_data['lieu_naissance'],
                sexe=validated_data['sexe'],
                telephone=validated_data['telephone'],
                email=validated_data['email'],
            )
            
            quitus_fresh.marquer_utilise(user)
            
            return user


class CreateAdminUserSerializer(serializers.Serializer):
    """Création d'utilisateurs admin par super_admin ou admin_academique"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    role = serializers.ChoiceField(choices=[
        ('admin_academique', 'Administrateur Académique'),
        ('responsable_filiere', 'Responsable de Filière'),
    ])
    filiere_id = serializers.IntegerField(required=False, allow_null=True)
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    send_email = serializers.BooleanField(default=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value
    
    def validate(self, data):
        request_user = self.context['request'].user
        target_role = data['role']
        
        # Vérifier les permissions
        if not request_user.can_create_role(target_role):
            raise serializers.ValidationError(
                f"Vous n'avez pas la permission de créer un utilisateur avec le rôle {target_role}."
            )
        
        # Si responsable_filiere, filiere_id obligatoire
        if target_role == 'responsable_filiere' and not data.get('filiere_id'):
            raise serializers.ValidationError({
                'filiere_id': 'La filière est obligatoire pour un responsable de filière.'
            })
        
        return data
    
    def create(self, validated_data):
        request_user = self.context['request'].user
        filiere_id = validated_data.pop('filiere_id', None)
        telephone = validated_data.pop('telephone', '')
        send_email = validated_data.pop('send_email', True)
        
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                nom=validated_data['nom'],
                prenom=validated_data['prenom'],
                role=validated_data['role'],
                created_by=request_user,
                is_email_verified=True
            )
            
            # Si responsable de filière, créer le profil
            if validated_data['role'] == 'responsable_filiere':
                from configurations.models import Filiere
                filiere = Filiere.objects.get(id=filiere_id) if filiere_id else None
                ResponsableFiliere.objects.create(
                    user=user,
                    filiere=filiere,
                    telephone=telephone
                )
            
            # Log l'action
            UserActionLog.objects.create(
                actor=request_user,
                target_user=user,
                action='create_user',
                details={
                    'role': validated_data['role'],
                    'email': validated_data['email']
                },
                ip_address=self.context['request'].META.get('REMOTE_ADDR')
            )
            
            # TODO: Envoyer email d'activation si send_email=True
            
            return user


class UpdateUserSerializer(serializers.ModelSerializer):
    """Modification d'un utilisateur"""
    class Meta:
        model = User
        fields = ['nom', 'prenom', 'email', 'is_active', 'role']
    
    def validate(self, data):
        request_user = self.context['request'].user
        target_user = self.instance
        
        # Vérifier si l'utilisateur peut gérer cet utilisateur
        if not request_user.can_manage_user(target_user):
            raise serializers.ValidationError(
                "Vous n'avez pas la permission de modifier cet utilisateur."
            )
        
        # Vérifier le changement de rôle
        if 'role' in data and data['role'] != target_user.role:
            if not request_user.can_create_role(data['role']):
                raise serializers.ValidationError({
                    'role': "Vous n'avez pas la permission d'attribuer ce rôle."
                })
        
        return data
    
    def update(self, instance, validated_data):
        request_user = self.context['request'].user
        
        with transaction.atomic():
            old_data = {
                'nom': instance.nom,
                'prenom': instance.prenom,
                'email': instance.email,
                'is_active': instance.is_active,
                'role': instance.role
            }
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Log l'action
            UserActionLog.objects.create(
                actor=request_user,
                target_user=instance,
                action='update_user',
                details={
                    'old': old_data,
                    'new': validated_data
                },
                ip_address=self.context['request'].META.get('REMOTE_ADDR')
            )
            
            return instance


class ResetPasswordSerializer(serializers.Serializer):
    """Réinitialisation de mot de passe par admin"""
    new_password = serializers.CharField(write_only=True, min_length=8)
    
    def save(self):
        request_user = self.context['request'].user
        target_user = self.context['target_user']
        
        if not request_user.can_manage_user(target_user):
            raise serializers.ValidationError(
                "Vous n'avez pas la permission de réinitialiser ce mot de passe."
            )
        
        target_user.set_password(self.validated_data['new_password'])
        target_user.save()
        
        # Log l'action
        UserActionLog.objects.create(
            actor=request_user,
            target_user=target_user,
            action='reset_password',
            details={'email': target_user.email},
            ip_address=self.context['request'].META.get('REMOTE_ADDR')
        )
        
        return target_user
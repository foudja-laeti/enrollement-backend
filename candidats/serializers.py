from rest_framework import serializers
from authentication.models import CodeQuitus
from .models import Candidat, Dossier, Document, Region, Departement
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings
import os

class CandidatEnrollementSerializer(serializers.Serializer):
    # ✅ PERSONNEL
    nom = serializers.CharField()
    prenom = serializers.CharField()
    date_naissance = serializers.DateField()
    lieu_naissance = serializers.CharField()
    sexe = serializers.ChoiceField(choices=[('M', 'M'), ('F', 'F')])
    ville = serializers.CharField()
    quartier = serializers.CharField(required=False)
    adresse_actuelle = serializers.CharField(required=False)
    
    # ✅ PARENTS
    nom_pere = serializers.CharField()
    tel_pere = serializers.CharField()
    nom_mere = serializers.CharField()
    tel_mere = serializers.CharField()
    telephone_secondaire = serializers.CharField()
    
    # ✅ RÉGIONS (ForeignKey IDs)
    region_id = serializers.IntegerField()
    departement_id = serializers.IntegerField()
    
    # ✅ ACADÉMIQUE (ForeignKey IDs)
    bac_id = serializers.IntegerField()
    serie_id = serializers.IntegerField()
    mention_id = serializers.IntegerField(required=False, allow_null=True)
    filiere_id = serializers.IntegerField()
    niveau_id = serializers.IntegerField(required=False, allow_null=True)
    centre_examen_id = serializers.IntegerField()
    centre_depot_id = serializers.IntegerField()
    etablissement_origine = serializers.CharField()
    annee_obtention_diplome = serializers.IntegerField()
    
    # ✅ FICHIERS
    code_quitus = serializers.CharField()
    photo_file = serializers.FileField()
    cni_file = serializers.FileField()
    diplome_file = serializers.FileField()

    def create(self, validated_data):
        from configurations.models import (
            Bac, Serie, Mention, Filiere, Niveau,
            CentreExamen, CentreDepot, AnneeScolaire
        )
        from .models import Candidat, Dossier, Document
        
        user = self.context['request'].user
        
        print(f"\n{'='*80}")
        print(f"🚀 DÉBUT SAUVEGARDE CANDIDAT")
        print(f"{'='*80}")
        
        # ✅ 1. RÉCUPÉRER OU CRÉER CANDIDAT
        candidat, created = Candidat.objects.get_or_create(user=user)
        print(f"📋 Candidat {'créé' if created else 'existant'}: {candidat.matricule}")
        
        # ✅ 2. EXTRAIRE LES FICHIERS AVANT DE LES SUPPRIMER DE validated_data
        photo_file = validated_data.pop('photo_file')
        cni_file = validated_data.pop('cni_file')
        diplome_file = validated_data.pop('diplome_file')
        code_quitus = validated_data.pop('code_quitus')
        
        print(f"\n📂 FICHIERS EXTRAITS:")
        print(f"  📸 Photo: {photo_file.name} ({photo_file.size} bytes)")
        print(f"  🆔 CNI: {cni_file.name} ({cni_file.size} bytes)")
        print(f"  🎓 Diplôme: {diplome_file.name} ({diplome_file.size} bytes)")
        
        # ✅ 3. EXTRAIRE LES IDs DES FOREIGNKEYS
        region_id = validated_data.pop('region_id')
        departement_id = validated_data.pop('departement_id')
        bac_id = validated_data.pop('bac_id')
        serie_id = validated_data.pop('serie_id')
        mention_id = validated_data.pop('mention_id', None)
        filiere_id = validated_data.pop('filiere_id')
        niveau_id = validated_data.pop('niveau_id', None)
        centre_examen_id = validated_data.pop('centre_examen_id')
        centre_depot_id = validated_data.pop('centre_depot_id')
        
        # ✅ 4. SAUVEGARDER TOUS LES CHAMPS SIMPLES
        for key, value in validated_data.items():
            setattr(candidat, key, value)
            print(f"  ✅ {key}: {value}")
        
        # ✅ 5. ASSIGNER LES FOREIGNKEYS
        candidat.region_id = region_id
        candidat.departement_id = departement_id
        candidat.bac_id = bac_id
        candidat.serie_id = serie_id
        candidat.mention_id = mention_id
        candidat.filiere_id = filiere_id
        candidat.niveau_id = niveau_id
        candidat.centre_examen_id = centre_examen_id
        candidat.centre_depot_id = centre_depot_id
        
        print(f"\n🔗 FOREIGNKEYS ASSIGNÉES:")
        print(f"  📍 Région: {region_id}, Département: {departement_id}")
        print(f"  🎓 BAC: {bac_id}, Série: {serie_id}, Mention: {mention_id}")
        print(f"  📚 Filière: {filiere_id}, Niveau: {niveau_id}")
        print(f"  🏛️ Centre examen: {centre_examen_id}, Centre dépôt: {centre_depot_id}")
        
        # ✅ 6. SAUVEGARDER PHYSIQUEMENT LA PHOTO ET METTRE À JOUR LE CHEMIN
        photo_dir = f"documents/photos/{candidat.matricule}"
        full_photo_dir = os.path.join(settings.MEDIA_ROOT, photo_dir)
        os.makedirs(full_photo_dir, exist_ok=True)
        
        photo_path = f"{photo_dir}/{photo_file.name}"
        
        # Sauvegarder le fichier sur le disque
        full_path = os.path.join(settings.MEDIA_ROOT, photo_path)
        with open(full_path, 'wb+') as destination:
            for chunk in photo_file.chunks():
                destination.write(chunk)
        
        candidat.photo_path = photo_path
        print(f"\n📸 PHOTO SAUVEGARDÉE: {photo_path}")
        
        # ✅ 7. MARQUER LE DOSSIER COMME COMPLET
        candidat.statut_dossier = 'complet'
        candidat.save()
        
        print(f"\n💾 CANDIDAT SAUVEGARDÉ: {candidat.matricule}")
        
        # ✅ 8. CRÉER LE DOSSIER
        annee = AnneeScolaire.objects.filter(is_active=True).first()
        dossier, created = Dossier.objects.get_or_create(
            candidat=candidat,
            defaults={
                'numero_dossier': f"DOS{candidat.id}-{timezone.now().year}",
                'annee_scolaire': annee,
                'statut': 'soumis'
            }
        )
        print(f"\n📁 DOSSIER {'créé' if created else 'existant'}: {dossier.numero_dossier}")
        
        # ✅ 9. SAUVEGARDER LES 3 DOCUMENTS (CNI, PHOTO, DIPLÔME)
        documents_data = [
            (photo_file, 'photo_identite', photo_path),
            (cni_file, 'cni', None),
            (diplome_file, 'diplome', None)
        ]
        
        print(f"\n📄 SAUVEGARDE DES DOCUMENTS:")
        for file_obj, doc_type, existing_path in documents_data:
            # Créer le répertoire pour chaque type de document
            doc_dir = f"documents/{doc_type}/{candidat.matricule}"
            full_doc_dir = os.path.join(settings.MEDIA_ROOT, doc_dir)
            os.makedirs(full_doc_dir, exist_ok=True)
            
            # Chemin du fichier
            if existing_path:
                file_path = existing_path
            else:
                file_path = f"{doc_dir}/{file_obj.name}"
                
                # Sauvegarder physiquement le fichier
                full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                with open(full_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
            
            # Créer l'enregistrement dans la BD
            # D'abord supprimer les anciens documents du même type pour éviter les doublons
            Document.objects.filter(
                candidat=candidat,
                dossier=dossier,
                type_document=doc_type
            ).delete()
            
            # Puis créer le nouveau document
            doc = Document.objects.create(
                candidat=candidat,
                dossier=dossier,
                type_document=doc_type,
                nom_fichier=file_obj.name,
                nom_original=file_obj.name,
                chemin_fichier=file_path,
                taille_fichier=file_obj.size,
                extension=os.path.splitext(file_obj.name)[1],
                mime_type=file_obj.content_type
            )
            doc_created = True
            
            print(f"  ✅ {doc_type.upper()}: {file_path} ({'créé' if doc_created else 'existant'})")
        
        print(f"\n{'='*80}")
        print(f"✅ ENRÔLEMENT COMPLET: {candidat.matricule}")
        print(f"{'='*80}\n")
        
        return candidat
# ✅ UNE SEULE DocumentSerializer (SUPPRIME l'autre)
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'candidat', 'dossier', 'inscription',
            'type_document', 'nom_fichier', 'nom_original',
            'chemin_fichier', 'taille_fichier', 'extension', 'mime_type',
            'is_verified', 'verified_by', 'verified_at',
            'commentaire_verification', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

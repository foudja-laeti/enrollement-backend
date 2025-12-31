# inscriptions/serializers.py
from rest_framework import serializers
from candidats.models import Candidat, Dossier, Document, Quitus
from configurations.models import AnneeScolaire, Filiere, Niveau, CentreExamen, CentreDepot, Diplome
from .models import Inscription
from django.db import transaction
from django.utils import timezone


class EnrollementSerializer(serializers.Serializer):
    quitus_code = serializers.CharField(max_length=6)

    # CANDIDAT (version simplifiée, tu complèteras)
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    date_naissance = serializers.DateField()
    lieu_naissance = serializers.CharField(max_length=255)
    sexe = serializers.ChoiceField(choices=Candidat.SEXE_CHOICES)
    telephone = serializers.CharField(max_length=20)
    email = serializers.EmailField()

    ville_residence = serializers.CharField(max_length=100)
    quartier_residence = serializers.CharField(max_length=100)

    # INSCRIPTION
    filiere = serializers.PrimaryKeyRelatedField(queryset=Filiere.objects.all())
    niveau = serializers.PrimaryKeyRelatedField(queryset=Niveau.objects.all())
    centre_examen = serializers.PrimaryKeyRelatedField(queryset=CentreExamen.objects.all())
    centre_depot = serializers.PrimaryKeyRelatedField(queryset=CentreDepot.objects.all())
    diplome = serializers.PrimaryKeyRelatedField(queryset=Diplome.objects.all())
    serie = serializers.CharField(max_length=100, required=False, allow_blank=True)
    annee_obtention_diplome = serializers.IntegerField()

    mention = serializers.ChoiceField(choices=Inscription.MENTION_CHOICES, required=False, allow_null=True)

    # FICHIERS
    cni_file = serializers.FileField()
    diplome_file = serializers.FileField()
    diplome_type = serializers.ChoiceField(choices=[("diplome", "Diplôme"), ("releve_notes", "Relevé")])

    def validate_quitus_code(self, value):
        try:
            quitus = Quitus.objects.get(code=value)
        except Quitus.DoesNotExist:
            raise serializers.ValidationError("Quitus inexistant.")
        if not quitus.is_used:
            raise serializers.ValidationError("Quitus non encore marqué comme utilisé.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        quitus_code = validated_data.pop("quitus_code")
        cni_file = validated_data.pop("cni_file")
        diplome_file = validated_data.pop("diplome_file")
        diplome_type = validated_data.pop("diplome_type")

        annee = AnneeScolaire.objects.filter(is_active=True).first()
        if not annee:
            raise serializers.ValidationError("Aucune année scolaire active.")

        # Candidat
        candidat, created = Candidat.objects.get_or_create(
            user=user,
            defaults={
                "nom": validated_data["nom"],
                "prenom": validated_data["prenom"],
                "date_naissance": validated_data["date_naissance"],
                "lieu_naissance": validated_data["lieu_naissance"],
                "sexe": validated_data["sexe"],
                "telephone": validated_data["telephone"],
                "email": validated_data["email"],
                "adresse_actuelle": f"{validated_data['quartier_residence']} - {validated_data['ville_residence']}",
                "ville": validated_data["ville_residence"],
                "pays": "Cameroun",
            },
        )

        # Dossier
        dossier, _ = Dossier.objects.get_or_create(
            candidat=candidat,
            annee_scolaire=annee,
            defaults={"statut": "ouvert"},
        )

        # Inscription
        inscription = Inscription.objects.create(
            candidat=candidat,
            dossier=dossier,
            annee_scolaire=annee,
            filiere=validated_data["filiere"],
            niveau=validated_data["niveau"],
            centre_examen=validated_data["centre_examen"],
            centre_depot=validated_data["centre_depot"],
            diplome=validated_data["diplome"],
            serie=validated_data.get("serie", ""),
            annee_obtention_diplome=validated_data["annee_obtention_diplome"],
            mention=validated_data.get("mention"),
            statut="brouillon",
        )

        # Documents (ici uniquement les métadonnées, tu brancheras le stockage disque plus tard)
        Document.objects.create(
            candidat=candidat,
            dossier=dossier,
            inscription=inscription,
            type_document="acte_naissance",   # ou un type CNI si tu ajoutes
            nom_fichier=cni_file.name,
            nom_original=cni_file.name,
            chemin_fichier="",
            taille_fichier=cni_file.size,
            extension=cni_file.name.split(".")[-1].lower(),
            mime_type=cni_file.content_type,
        )

        doc_type = "diplome" if diplome_type == "diplome" else "releve_notes"
        Document.objects.create(
            candidat=candidat,
            dossier=dossier,
            inscription=inscription,
            type_document=doc_type,
            nom_fichier=diplome_file.name,
            nom_original=diplome_file.name,
            chemin_fichier="",
            taille_fichier=diplome_file.size,
            extension=diplome_file.name.split(".")[-1].lower(),
            mime_type=diplome_file.content_type,
        )

        return inscription

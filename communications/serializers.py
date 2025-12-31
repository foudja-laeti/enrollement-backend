from rest_framework import serializers
from .models import Categorie, Actualite, Notification , Epreuve


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = '__all__'


class ActualiteSerializer(serializers.ModelSerializer):
    auteur_email = serializers.EmailField(source='auteur.email', read_only=True)
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    
    class Meta:
        model = Actualite
        fields = [
            'id', 'titre', 'slug', 'contenu', 'extrait', 'image_path',
            'categorie', 'categorie_nom', 'auteur', 'auteur_email',
            'is_published', 'date_publication', 'meta_description',
            'meta_keywords', 'vues', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'vues', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['created_at']



class EpreuveSerializer(serializers.ModelSerializer):
    filiere = serializers.CharField(source='filiere.libelle')
    fichier_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Epreuve
        fields = [
            'id', 'titre', 'slug', 'description',
            'filiere',  # ✅ String (libelle)
            'annee', 
            'fichier_url', 'taille',
            'nombre_telechargements',
            'created_at'
        ]
    
    def get_fichier_url(self, obj):
        request = self.context.get('request')
        if obj.fichier and request:
            return request.build_absolute_uri(obj.fichier.url)
        return None

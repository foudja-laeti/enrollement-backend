from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import FileResponse
from .models import Epreuve
from .serializers import EpreuveSerializer

class EpreuveViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour les anciennes épreuves
    - GET /api/epreuves/ : Liste toutes les épreuves
    - GET /api/epreuves/{id}/ : Détail d'une épreuve
    - GET /api/epreuves/{id}/telecharger/ : Télécharger une épreuve
    """
    queryset = Epreuve.objects.filter(is_published=True)
    serializer_class = EpreuveSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtres optionnels
        filiere = self.request.query_params.get('filiere')
        annee = self.request.query_params.get('annee')
        session = self.request.query_params.get('session')
        
        if filiere:
            queryset = queryset.filter(filiere=filiere)
        if annee:
            queryset = queryset.filter(annee=annee)
        if session:
            queryset = queryset.filter(session=session)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def telecharger(self, request, pk=None):
        """Télécharger une épreuve"""
        epreuve = self.get_object()
        epreuve.incrementer_telechargements()
        
        response = FileResponse(epreuve.fichier.open('rb'))
        response['Content-Disposition'] = f'attachment; filename="{epreuve.slug}.pdf"'
        return response
   
    
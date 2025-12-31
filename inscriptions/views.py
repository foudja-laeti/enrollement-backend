# inscriptions/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .serializers import EnrollementSerializer


class EnrollementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EnrollementSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            inscription = serializer.save()
            return Response(
                {"message": "Enrôlement enregistré", "inscription_id": inscription.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

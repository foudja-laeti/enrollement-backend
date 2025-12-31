# communications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EpreuveViewSet

router = DefaultRouter()
router.register(r'epreuves', EpreuveViewSet, basename='epreuve')

urlpatterns = [
    path('', include(router.urls)),
]
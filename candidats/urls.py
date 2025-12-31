# candidats/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('enrollement/', views.enrollement_view, name='enrollement'),
    #path('check-quitus/<str:quitus_code>/', views.check_quitus, name='check-quitus'),
  
  # path('mon-dossier/', views.mon_dossier_view, name='mon-dossier'),
]
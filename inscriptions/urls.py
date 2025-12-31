# inscriptions/urls.py
from django.urls import path
from .views import EnrollementView

urlpatterns = [
    path("enrollement/", EnrollementView.as_view(), name="enrollement"),
]

from django.urls import path, include
from .core import models_list
from .views import home

urlpatterns = [
    path("", home, name="home"),
    path("", include("evaluations.runs.urls")),
    path("", include("evaluations.arc.urls")),
    
    path("api/models/", models_list, name="api_models_list"),
]
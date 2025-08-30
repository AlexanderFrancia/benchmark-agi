from django.urls import path
from . import views
from .api import models_list

urlpatterns = [
    path("", views.home, name="home"),
    path("api/models/", models_list, name="api_models_list"),
    path("arc/", views.arc_index, name="arc_index"),
    path("arc/<str:task_id>/", views.arc_detail, name="arc_detail"),
    path("arc/<str:task_id>/evaluate/", views.arc_evaluate, name="arc_evaluate"),
]
from django.urls import path
from . import views
from .api import models_list

urlpatterns = [
    # Home / listado
    path("", views.arc_index, name="home"),
    path("arc/", views.arc_index, name="arc_index"),

    # ---- Rutas FIJAS (deben ir antes de las dinámicas con <str:task_id>) ----
    path("arc/evaluate_dataset_live/", views.start_arc_dataset_live, name="arc_evaluate_dataset_live"),
    path("arc/evaluate_dataset/", views.arc_evaluate_dataset, name="arc_evaluate_dataset"),
    path("arc/run/<uuid:run_id>/", views.arc_run_live_page, name="arc_run_live"),
    path("arc/run/<uuid:run_id>/status/", views.arc_run_status, name="arc_run_status"),

    # API
    path("api/models/", models_list, name="api_models_list"),

    # ---- Rutas por tarea ----
    path("arc/<str:task_id>/evaluate/", views.arc_evaluate, name="arc_evaluate"),
    path("arc/<str:task_id>/", views.arc_detail, name="arc_detail"),
]
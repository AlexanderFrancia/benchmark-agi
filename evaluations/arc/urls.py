from django.urls import path
from . import views

urlpatterns = [
    path("arc/", views.arc_index, name="arc_index"),
    path("arc/evaluate_dataset/", views.evaluate_dataset, name="arc_evaluate_dataset"),
    path("arc/evaluate_dataset_live/", views.evaluate_dataset_live, name="arc_evaluate_dataset_live"),
    path("arc/<str:task_id>/", views.detail, name="arc_detail"),
    path("arc/<str:task_id>/evaluate/", views.evaluate, name="arc_evaluate"),
]

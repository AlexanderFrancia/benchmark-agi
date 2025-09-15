from django.urls import path
from . import views

app_name = "maze"

urlpatterns = [
    path("", views.maze_index, name="maze_index"),
    path("<slug:maze_id>/", views.maze_detail, name="maze_detail"),
    path("<slug:maze_id>/evaluate/", views.maze_evaluate, name="maze_evaluate"),
    path("evaluate_dataset/", views.maze_evaluate_dataset, name="maze_evaluate_dataset"),
]

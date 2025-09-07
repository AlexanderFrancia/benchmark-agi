from django.urls import path
from . import views

urlpatterns = [
    path("run/<uuid:run_id>/", views.run_live_page, name="run_live"),
    path("run/<uuid:run_id>/status/", views.run_status, name="run_status"),
]

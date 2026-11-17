from django.urls import path

from . import views

app_name = "practice"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("actividades/", views.activities, name="activities"),
    path("actividades/<int:pk>/", views.activity, name="activity"),
    path("materiales/", views.materials, name="materials"),
    path("materiales/<int:pk>/", views.material, name="material"),
    path("materiales/<int:pk>/imprimir/", views.material_print, name="material_print"),
    path("pictogramas/", views.pictograms, name="pictograms"),
    path("agenda-visual/", views.agenda, name="agenda"),
    path("videos/", views.videos, name="videos"),
    path("videos/<int:pk>/", views.video, name="video"),
]

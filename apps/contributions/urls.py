from django.urls import path

from . import views

app_name = "contributions"

urlpatterns = [
    path("", views.index, name="index"),
    path("mis-contribuciones/", views.mine, name="mine"),
    path("nueva/<slug:type_slug>/", views.create, name="create"),
    path("<str:model_key>/<int:pk>/", views.summary, name="summary"),
    path("<str:model_key>/<int:pk>/editar/", views.edit, name="edit"),
    path("<str:model_key>/<int:pk>/<str:action>/", views.act, name="act"),
]

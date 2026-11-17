from django.urls import path

from . import views

app_name = "learn"

urlpatterns = [
    path("", views.index, name="index"),
    path("capsula/<int:pk>/", views.capsule, name="capsule"),
    path("preguntas-frecuentes/", views.faq, name="faq"),
]

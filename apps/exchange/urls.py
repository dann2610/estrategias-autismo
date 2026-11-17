from django.urls import path

from . import views

app_name = "exchange"

urlpatterns = [
    path("", views.index, name="index"),
    path("reglas/", views.rules, name="rules"),
    path("<int:pk>/", views.item, name="detail"),
    path("<int:pk>/disponibilidad/", views.set_availability, name="availability"),
]

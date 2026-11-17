from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("nuevo/", views.create_report, name="create"),
    path("nuevo/<str:model_key>/<int:pk>/", views.create_report, name="create_for"),
]

from django.urls import path

from . import views

app_name = "comments"

urlpatterns = [
    path("capsula/<int:pk>/", views.add, name="add"),
]

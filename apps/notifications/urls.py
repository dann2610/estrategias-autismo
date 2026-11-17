from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/abrir/", views.open_notification, name="open"),
    path("marcar-leidas/", views.mark_all_read, name="mark_all"),
]

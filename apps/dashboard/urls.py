from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("pendientes/", views.inbox, name="inbox"),
    path("revisar/<str:model_key>/<int:pk>/", views.review, name="review"),
    path("revisar/<str:model_key>/<int:pk>/accion/", views.act, name="act"),
    path("revisar/<str:model_key>/<int:pk>/eliminar/", views.delete, name="delete"),
    path("reportes/", views.reports, name="reports"),
    path("reportes/<int:pk>/resolver/", views.resolve_report, name="resolve_report"),
    path("usuarios/", views.users, name="users"),
    path("usuarios/<int:pk>/estado/", views.toggle_user, name="toggle_user"),
    path("estadisticas/", views.stats, name="stats"),
    path("auditoria/", views.audit_log, name="audit"),
    path("historial/", views.moderation_history, name="history"),
    path("calidad/", views.quality, name="quality"),
]

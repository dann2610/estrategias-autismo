from django.contrib import admin
from django.urls import include, path

from apps.core import api
from apps.notifications.views import unread_count

admin.site.site_header = "Estrategias de apoyo en el autismo · Administración"
admin.site.site_title = "Administración"
admin.site.index_title = "Gestión de contenidos"

urlpatterns = [
    path("", include("apps.core.urls")),
    path("comprender/", include("apps.learn.urls")),
    path("actividades-y-recursos/", include("apps.practice.urls")),
    path("orientacion/directorio/", include("apps.directory.urls")),
    path("orientacion/entrevistas/", include("apps.interviews.urls")),
    path("orientacion/intercambio/", include("apps.exchange.urls")),
    path("comentarios/", include("apps.comments.urls")),
    path("participar/", include("apps.contributions.urls")),
    path("cuenta/", include("apps.accounts.urls")),
    path("notificaciones/", include("apps.notifications.urls")),
    path("reportar/", include("apps.reports.urls")),
    path("panel/", include("apps.dashboard.urls")),
    # Django Admin en una ruta no obvia; solo para personal autorizado (is_staff)
    path("gestion-django/", admin.site.urls),
    path("api/actividades/", api.ActivityList.as_view(), name="api_activities"),
    path("api/pictogramas/", api.PictogramList.as_view(), name="api_pictograms"),
    path("api/notificaciones/no-leidas/", unread_count, name="api_unread"),
]

handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
handler403 = "apps.core.views.error_403"

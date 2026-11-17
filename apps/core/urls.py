from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("orientacion/", views.orientation, name="orientation"),
    path("buscar/", views.search, name="search"),
    path("tema/<slug:slug>/", views.topic, name="topic"),
    path("fuentes/", views.sources, name="sources"),
    path("favorito/<str:model_key>/<int:pk>/", views.toggle_favorite, name="favorite"),
    path("archivo/<str:model_key>/<int:pk>/<str:field>/", views.serve_file, name="file"),
    path("sobre-el-proyecto/", views.static_page("pages/about.html"), name="about"),
    path("privacidad/", views.static_page("pages/privacy.html"), name="privacy"),
    path("accesibilidad/", views.static_page("pages/accessibility.html"), name="accessibility"),
    path("terminos/", views.static_page("pages/terms.html"), name="terms"),
    path("normas-de-convivencia/", views.static_page("pages/rules.html"), name="rules"),
    path("creditos/", views.static_page("pages/credits.html"), name="credits"),
]

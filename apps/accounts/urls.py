from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("registro/", views.signup, name="signup"),
    path("ingresar/", views.LoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("mi-cuenta/", views.panel, name="panel"),
    path("mi-cuenta/perfil/", views.edit_profile, name="profile"),
    path("mi-cuenta/favoritos/", views.favorites, name="favorites"),
    path("mi-cuenta/contrasena/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/form_simple.html",
        extra_context={"title": "Cambiar contraseña"},
        success_url=reverse_lazy("accounts:password_change_done")), name="password_change"),
    path("mi-cuenta/contrasena/lista/", auth_views.PasswordChangeDoneView.as_view(
        template_name="accounts/message.html",
        extra_context={"title": "Contraseña actualizada",
                       "text": "Tu contraseña se cambió correctamente."}), name="password_change_done"),
    path("recuperar/", auth_views.PasswordResetView.as_view(
        template_name="accounts/form_simple.html",
        email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        extra_context={"title": "Recuperar contraseña",
                       "intro": "Escribe tu correo y te enviaremos un enlace para crear una nueva contraseña."},
        success_url=reverse_lazy("accounts:password_reset_done")), name="password_reset"),
    path("recuperar/enviado/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/message.html",
        extra_context={"title": "Revisa tu correo",
                       "text": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."}),
         name="password_reset_done"),
    path("recuperar/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/form_simple.html", extra_context={"title": "Nueva contraseña"},
        success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("recuperar/listo/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/message.html",
        extra_context={"title": "Contraseña restablecida", "text": "Ya puedes iniciar sesión."}),
         name="password_reset_complete"),
]

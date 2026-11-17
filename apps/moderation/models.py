from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.choices import Status


class ModerationAction(models.Model):
    """Historial de decisiones sobre cada contribución (quién, cuándo, qué y por qué)."""

    class Action(models.TextChoices):
        CREATE = "crear", "Creación de borrador"
        SUBMIT = "enviar", "Envío a revisión"
        RESUBMIT = "reenviar", "Reenvío tras correcciones"
        START_REVIEW = "iniciar", "Inicio de revisión"
        APPROVE = "aprobar", "Aprobación y publicación"
        REJECT = "rechazar", "Rechazo"
        REQUEST_CHANGES = "solicitar_cambios", "Solicitud de cambios"
        EDIT_AUTHOR = "editar_autor", "Edición del autor"
        EDIT_ADMIN = "editar_admin", "Edición administrativa"
        WITHDRAW = "retirar", "Retiro por el autor"
        UNPUBLISH = "despublicar", "Despublicación"
        ARCHIVE = "archivar", "Archivo"
        RESTORE = "restaurar", "Restauración"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                              related_name="moderation_actions")
    action = models.CharField(max_length=30, choices=Action.choices)
    from_status = models.CharField(max_length=20, choices=Status.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=Status.choices, blank=True)
    comment = models.TextField(blank=True)
    changes = models.JSONField("campos modificados", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]
        verbose_name = "acción de moderación"
        verbose_name_plural = "historial de moderación"
        permissions = [
            ("moderate_content", "Puede revisar y moderar contenido"),
            ("manage_users", "Puede gestionar cuentas de usuario"),
            ("view_statistics", "Puede ver estadísticas"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} · {self.created_at:%d/%m/%Y %H:%M}"


class AuditLog(models.Model):
    """Registro de acciones administrativas relevantes. No guarda contraseñas ni datos sensibles."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                              related_name="audit_entries")
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registro de auditoría"

    def __str__(self):
        return f"{self.action} · {self.target}"

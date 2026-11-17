from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Report(models.Model):
    class Reason(models.TextChoices):
        INCORRECT = "incorrecta", "Información incorrecta"
        OUTDATED = "desactualizada", "Información desactualizada"
        INAPPROPRIATE = "inapropiado", "Contenido inapropiado u ofensivo"
        PRIVACY = "privacidad", "Expone datos personales o de un menor"
        SUSPICIOUS = "sospechoso", "Anuncio o perfil sospechoso"
        RIGHTS = "derechos", "Posible infracción de derechos de autor"
        OTHER = "otro", "Otro motivo"

    class State(models.TextChoices):
        OPEN = "abierto", "Sin resolver"
        RESOLVED = "resuelto", "Resuelto"
        DISMISSED = "descartado", "Descartado"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="reports_made")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    item = GenericForeignKey("content_type", "object_id")
    reference = models.CharField("página o contenido (si no se reporta desde una ficha)", max_length=300,
                                 blank=True)
    reason = models.CharField("motivo", max_length=20, choices=Reason.choices)
    details = models.TextField("detalles", max_length=2000)
    state = models.CharField(max_length=12, choices=State.choices, default=State.OPEN, db_index=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="reports_resolved")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField("resolución", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "reporte"
        verbose_name_plural = "reportes"

    def __str__(self):
        return f"{self.get_reason_display()} · {self.created_at:%d/%m/%Y}"

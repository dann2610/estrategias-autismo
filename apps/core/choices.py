"""Opciones compartidas entre módulos."""
from django.db import models


class Status(models.TextChoices):
    DRAFT = "borrador", "Borrador"
    PENDING = "pendiente", "Pendiente de revisión"
    IN_REVIEW = "en_revision", "En revisión"
    CHANGES = "cambios", "Cambios solicitados"
    APPROVED = "aprobado", "Aprobado / publicado"
    REJECTED = "rechazado", "Rechazado"
    WITHDRAWN = "retirado", "Retirado"
    ARCHIVED = "archivado", "Archivado"


class Origin(models.TextChoices):
    EDITORIAL = "editorial", "Información educativa revisada"
    INSTITUTIONAL = "institucional", "Información institucional"
    COMMUNITY = "comunidad", "Aporte de la comunidad"
    PENDING_CHECK = "por_verificar", "Pendiente de verificación"


class AgeRange(models.TextChoices):
    A3_5 = "3-5", "3 a 5 años"
    A6_8 = "6-8", "6 a 8 años"
    A9_12 = "9-12", "9 a 12 años"
    ALL = "todas", "De 3 a 12 años"


PROVINCES = [
    "Azuay", "Bolívar", "Cañar", "Carchi", "Chimborazo", "Cotopaxi", "El Oro", "Esmeraldas",
    "Galápagos", "Guayas", "Imbabura", "Loja", "Los Ríos", "Manabí", "Morona Santiago", "Napo",
    "Orellana", "Pastaza", "Pichincha", "Santa Elena", "Santo Domingo de los Tsáchilas",
    "Sucumbíos", "Tungurahua", "Zamora Chinchipe", "Todo el país",
]
PROVINCE_CHOICES = [(p, p) for p in PROVINCES]

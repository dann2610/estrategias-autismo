from django.db import models
from django.urls import reverse

from apps.core.choices import PROVINCE_CHOICES
from apps.core.models import ModeratedContent, Topic
from apps.core.validators import upload_path, validate_upload


class Institution(ModeratedContent):
    """Directorio de instituciones y servicios. Solo se publica con evidencia verificable."""
    TYPE_LABEL = "Institución o servicio"
    PRIVATE_FILE_FIELDS = ("evidence_document",)

    class Kind(models.TextChoices):
        FAMILY_ASSOCIATION = "asociacion", "Asociación de familias"
        FOUNDATION = "fundacion", "Fundación u organización social"
        PUBLIC_SERVICE = "servicio_publico", "Servicio público"
        HEALTH = "salud", "Servicio de salud"
        THERAPY = "terapeutico", "Centro terapéutico"
        SCHOOL = "educativa", "Institución educativa con programa de inclusión"
        PROCEDURE = "tramite", "Trámite u orientación oficial"

    class Cost(models.TextChoices):
        FREE = "gratuito", "Gratuito según la fuente"
        PAID = "pagado", "Con costo"
        MIXED = "mixto", "Gratuito y con costo"
        UNKNOWN = "no_informado", "Costo no informado"

    class Basis(models.TextChoices):
        ACCREDITATION = "acreditacion", "Acreditación oficial"
        AUTHORIZATION = "autorizacion", "Autorización de funcionamiento"
        REGISTRY = "registro", "Registro institucional"
        PUBLIC_INFO = "informacion_publica", "Información pública verificada"
        SELF = "autodescripcion", "Descripción aportada por la institución"
        PENDING = "pendiente", "Pendiente de verificación"

    BASIS_HELP = {
        "acreditacion": "Un organismo competente certificó que cumple estándares definidos.",
        "autorizacion": "Una autoridad permitió su funcionamiento. No implica evaluación de calidad.",
        "registro": "Consta en un registro oficial. No implica evaluación de calidad.",
        "informacion_publica": "Los datos provienen de fuentes públicas citadas (sitio oficial o prensa). "
                               "No implica acreditación ni recomendación clínica.",
        "autodescripcion": "La información fue aportada por la propia institución y no ha sido contrastada.",
        "pendiente": "Aún no se verifica la información.",
    }

    kind = models.CharField("tipo de institución", max_length=20, choices=Kind.choices, db_index=True)
    services = models.TextField("servicios", help_text="Uno por línea.")
    inclusion_services = models.TextField("servicios o programas de inclusión educativa", blank=True)
    population = models.CharField("población atendida", max_length=200, blank=True)
    province = models.CharField("provincia", max_length=40, choices=PROVINCE_CHOICES, default="Guayas", db_index=True)
    canton = models.CharField("cantón o localidad", max_length=60, db_index=True)
    address = models.CharField("dirección pública", max_length=250, blank=True)
    phone = models.CharField("teléfono público", max_length=60, blank=True)
    email = models.EmailField("correo público", blank=True)
    website = models.URLField("sitio web oficial", blank=True)
    social = models.URLField("red social oficial", blank=True)
    cost = models.CharField("costo", max_length=15, choices=Cost.choices, default=Cost.UNKNOWN)
    verification_basis = models.CharField("base de la verificación", max_length=20, choices=Basis.choices,
                                          default=Basis.PENDING)
    evidence_url = models.URLField("fuente de verificación", max_length=500, blank=True)
    evidence_note = models.CharField("nota de verificación", max_length=300, blank=True,
                                     help_text="Qué se verificó y en qué fuente.")
    evidence_document = models.FileField("documento de respaldo (privado)", upload_to=upload_path, blank=True,
                                         validators=[validate_upload])
    last_reviewed = models.DateField("fecha de última revisión", null=True, blank=True)
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="institutions")

    class Meta(ModeratedContent.Meta):
        ordering = ["province", "canton", "title"]
        verbose_name = "institución o servicio"
        verbose_name_plural = "directorio de instituciones"

    def get_absolute_url(self):
        return reverse("directory:detail", args=[self.pk])

    @property
    def basis_help(self):
        return self.BASIS_HELP.get(self.verification_basis, "")

    def publication_problems(self):
        problems = []
        if self.verification_basis == self.Basis.PENDING:
            problems.append("Indique la base de la verificación antes de publicar.")
        if not (self.evidence_url or self.evidence_document):
            problems.append("Agregue la fuente o el documento que respalda la información.")
        if not self.last_reviewed:
            problems.append("Indique la fecha de la última revisión.")
        return problems

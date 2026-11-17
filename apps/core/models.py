from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .choices import Origin, Status


class ModeratedQuerySet(models.QuerySet):
    def public(self):
        """Solo el contenido aprobado es visible en páginas, búsquedas y API públicas."""
        return self.filter(status=Status.APPROVED)

    def owned_by(self, user):
        return self.filter(author=user)


class ModeratedContent(models.Model):
    """
    Base de todo contenido que se publica previa revisión. El estado cambia únicamente
    mediante apps.moderation.services.transition(), que valida, registra y notifica.
    """

    TYPE_LABEL = "Contenido"
    PUBLIC_FILE_FIELDS: tuple = ()
    PRIVATE_FILE_FIELDS: tuple = ()

    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción breve")
    status = models.CharField("estado", max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    origin = models.CharField("tipo de información", max_length=20, choices=Origin.choices, default=Origin.EDITORIAL)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="autor", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("última modificación", auto_now=True)
    submitted_at = models.DateTimeField("enviado a revisión", null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="revisado por", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField("fecha de revisión", null=True, blank=True)
    review_comment = models.TextField("comentario de moderación", blank=True)
    featured = models.BooleanField("destacado en inicio", default=False)
    view_count = models.PositiveIntegerField("visitas", default=0, editable=False)

    objects = ModeratedQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    @property
    def is_public(self):
        return self.status == Status.APPROVED

    @property
    def author_can_edit(self):
        return self.status in (Status.DRAFT, Status.PENDING, Status.CHANGES, Status.REJECTED, Status.WITHDRAWN,
                               Status.APPROVED)

    @property
    def model_key(self):
        return f"{self._meta.app_label}.{self._meta.model_name}"

    @property
    def is_community(self):
        return self.origin == Origin.COMMUNITY

    def publication_problems(self):
        """Lista de motivos por los que el contenido aún no puede publicarse (vacía si puede)."""
        return []


class Topic(models.Model):
    """Tema compartido: conecta cápsulas, actividades, materiales, videos, entrevistas y fuentes."""
    name = models.CharField("nombre", max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    description = models.CharField("descripción", max_length=200, blank=True)
    pictogram = models.CharField("pictograma (código)", max_length=40, blank=True,
                                 help_text="Código Twemoji del archivo en static/picto, p. ej. 1f4ac")
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "tema"
        verbose_name_plural = "temas (etiquetas compartidas)"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:70]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:topic", args=[self.slug])


class Source(models.Model):
    """Referencia bibliográfica realmente consultada (APA 7)."""

    class Kind(models.TextChoices):
        LEGAL = "legal", "Norma jurídica oficial"
        OFFICIAL = "oficial", "Organismo oficial o sanitario"
        SCIENTIFIC = "cientifica", "Publicación científica"
        PRESS = "prensa", "Prensa"
        RESOURCE = "recurso", "Recurso educativo"

    citation = models.TextField("referencia APA 7", help_text="Sin la URL; se agrega aparte.")
    short = models.CharField("cita en el texto", max_length=120, help_text="Ej.: (OMS, 2025)")
    url = models.URLField("enlace", max_length=500, blank=True)
    kind = models.CharField("tipo de fuente", max_length=12, choices=Kind.choices, default=Kind.OFFICIAL)
    accessed_on = models.DateField("fecha de consulta")
    notes = models.CharField("nota de uso", max_length=300, blank=True,
                             help_text="Qué se tomó de esta fuente o advertencias de vigencia.")
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="sources")

    class Meta:
        ordering = ["citation"]
        verbose_name = "fuente bibliográfica"
        verbose_name_plural = "fuentes bibliográficas"

    def __str__(self):
        return self.short


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "content_type", "object_id"], name="favorito_unico")]
        indexes = [models.Index(fields=["content_type", "object_id"])]
        ordering = ["-created_at"]
        verbose_name = "favorito"


class SiteConfig(models.Model):
    """Configuración general editable por el administrador (registro único)."""
    notice = models.CharField("aviso general en el sitio", max_length=300, blank=True)
    contact_email = models.EmailField("correo de contacto público", blank=True)
    allow_comments = models.BooleanField("permitir comentarios en las cápsulas", default=True)
    allow_exchange = models.BooleanField("habilitar el intercambio de materiales", default=True)

    class Meta:
        verbose_name = "configuración del sitio"
        verbose_name_plural = "configuración del sitio"

    def __str__(self):
        return "Configuración del sitio"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

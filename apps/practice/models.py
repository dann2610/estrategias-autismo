import re

from django.core.exceptions import ValidationError
from django.db import models
from django.templatetags.static import static
from django.urls import reverse

from apps.core.choices import AgeRange, Origin
from apps.core.models import ModeratedContent, Source, Topic
from apps.core.validators import upload_path, validate_upload

TWEMOJI_CREDIT = "Twemoji, © Twitter, Inc. y otros colaboradores"
TWEMOJI_LICENSE = "CC BY 4.0"
TWEMOJI_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/deed.es"


class Audience(models.TextChoices):
    FAMILIES = "familias", "Familias y cuidadores"
    TEACHERS = "docentes", "Docentes"
    BOTH = "ambos", "Familias y docentes"


class Pictogram(models.Model):
    class Category(models.TextChoices):
        ROUTINE = "rutina", "Rutinas"
        EMOTION = "emocion", "Emociones"
        NEED = "necesidad", "Necesidades y pedidos"
        PLACE = "lugar", "Lugares y salidas"
        ACTION = "accion", "Acciones y juego"

    code = models.CharField("código", max_length=60, unique=True,
                            help_text="Nombre del archivo en static/picto sin extensión, o un código propio.")
    label = models.CharField("texto", max_length=40)
    category = models.CharField("categoría", max_length=12, choices=Category.choices)
    image = models.ImageField("imagen propia (opcional)", upload_to="pictogramas/", blank=True,
                              validators=[validate_upload],
                              help_text="Si se sube, reemplaza al archivo del banco.")
    credit = models.CharField("autoría", max_length=120, default=TWEMOJI_CREDIT)
    license = models.CharField("licencia", max_length=40, default=TWEMOJI_LICENSE)
    order = models.PositiveSmallIntegerField("orden", default=0)
    active = models.BooleanField("visible", default=True)

    class Meta:
        ordering = ["category", "order", "label"]
        verbose_name = "pictograma"
        verbose_name_plural = "banco de pictogramas"

    def __str__(self):
        return self.label

    @property
    def src(self):
        return self.image.url if self.image else static(f"picto/{self.code}.svg")


class Activity(ModeratedContent):
    """Área 2: actividad con objetivo, materiales, instrucciones, edad, adaptaciones y precauciones."""
    TYPE_LABEL = "Actividad"

    class Kind(models.TextChoices):
        GAME = "juego", "Juego educativo"
        COMMUNICATION = "comunicacion", "Comunicación"
        EMOTIONS = "emociones", "Emociones"
        ROUTINES = "rutinas", "Rutinas cotidianas"
        CLASSROOM = "aula", "Adaptación para el aula"
        AUTONOMY = "autonomia", "Autonomía"

    class Duration(models.TextChoices):
        D5 = "5", "Unos 5 minutos"
        D15 = "15", "Unos 15 minutos"
        D30 = "30", "30 minutos o más"

    class Place(models.TextChoices):
        HOME = "hogar", "Hogar"
        SCHOOL = "escuela", "Escuela"
        BOTH = "ambos", "Hogar y escuela"

    kind = models.CharField("tipo", max_length=15, choices=Kind.choices, db_index=True)
    age_range = models.CharField("edad orientativa", max_length=6, choices=AgeRange.choices, default=AgeRange.ALL)
    duration = models.CharField("duración", max_length=3, choices=Duration.choices, default=Duration.D15)
    place = models.CharField("lugar", max_length=10, choices=Place.choices, default=Place.BOTH)
    objective = models.CharField("objetivo orientativo", max_length=300)
    materials_needed = models.TextField("materiales", help_text="Uno por línea.")
    instructions = models.TextField("instrucciones", help_text="Un paso por línea.")
    adaptations = models.TextField("adaptaciones", help_text="Una por línea.")
    precautions = models.TextField("precauciones", help_text="Una por línea.")
    related_materials = models.ManyToManyField("Material", verbose_name="materiales imprimibles", blank=True,
                                               related_name="activities")
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="activities")
    sources = models.ManyToManyField(Source, verbose_name="fuentes", blank=True, related_name="activities")

    class Meta(ModeratedContent.Meta):
        ordering = ["-featured", "title"]
        verbose_name = "actividad"
        verbose_name_plural = "actividades"

    def get_absolute_url(self):
        return reverse("practice:activity", args=[self.pk])


class Material(ModeratedContent):
    """Apoyo visual o material descargable. Los imprimibles se generan desde el banco de pictogramas."""
    TYPE_LABEL = "Material"
    PUBLIC_FILE_FIELDS = ("file",)

    class Kind(models.TextChoices):
        AGENDA = "agenda", "Agenda visual"
        SEQUENCE = "secuencia", "Secuencia de pasos"
        CARDS = "tarjetas", "Tarjetas"
        BOARD = "tablero", "Tablero de comunicación"
        FIRST_THEN = "primero", "Tablero Primero / Después"
        WORKSHEET = "ficha", "Ficha para completar"
        GAME = "juego", "Juego imprimible"
        DOCUMENT = "documento", "Documento o plantilla"

    class Layout(models.TextChoices):
        SEQUENCE = "secuencia", "Secuencia numerada"
        GRID = "cuadricula", "Cuadrícula de tarjetas"
        PAIRS = "pares", "Pares para juego de memoria"
        FIRST_THEN = "primero", "Primero / Después"
        CARD = "tarjeta", "Tarjeta única grande"
        WORKSHEET = "ficha", "Ficha con preguntas"
        FILE = "archivo", "Archivo o enlace externo"

    kind = models.CharField("tipo", max_length=12, choices=Kind.choices)
    layout = models.CharField("formato", max_length=12, choices=Layout.choices, default=Layout.GRID)
    how_to_use = models.TextField("cómo usarlo", help_text="Un paso por línea.")
    worksheet_prompts = models.TextField("preguntas de la ficha", blank=True, help_text="Una por línea.")
    file = models.FileField("archivo (PDF, PNG o JPG)", upload_to=upload_path, blank=True, validators=[validate_upload])
    external_url = models.URLField("enlace externo legítimo", blank=True)
    credit = models.CharField("autoría y créditos", max_length=250, blank=True)
    license = models.CharField("licencia o permiso de uso", max_length=120, blank=True)
    rights_confirmed = models.BooleanField("confirmó tener derechos para compartir", default=False)
    age_range = models.CharField("edad orientativa", max_length=6, choices=AgeRange.choices, default=AgeRange.ALL)
    audience = models.CharField("público", max_length=10, choices=Audience.choices, default=Audience.BOTH)
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="materials")

    class Meta(ModeratedContent.Meta):
        ordering = ["-featured", "title"]
        verbose_name = "material"
        verbose_name_plural = "materiales y apoyos visuales"

    def get_absolute_url(self):
        return reverse("practice:material", args=[self.pk])

    @property
    def is_printable(self):
        return self.layout != self.Layout.FILE

    def publication_problems(self):
        problems = []
        if self.layout == self.Layout.FILE and not (self.file or self.external_url):
            problems.append("El material no tiene archivo ni enlace.")
        if self.layout in (self.Layout.SEQUENCE, self.Layout.GRID, self.Layout.PAIRS, self.Layout.FIRST_THEN,
                           self.Layout.CARD) and self.pk and not self.items.exists():
            problems.append("El imprimible no tiene pictogramas.")
        if self.layout == self.Layout.WORKSHEET and not self.worksheet_prompts.strip():
            problems.append("La ficha no tiene preguntas.")
        if self.origin == Origin.COMMUNITY and not self.rights_confirmed:
            problems.append("El autor no confirmó tener derechos para compartir el material.")
        return problems


class MaterialItem(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="items")
    pictogram = models.ForeignKey(Pictogram, on_delete=models.PROTECT, verbose_name="pictograma")
    label = models.CharField("texto personalizado", max_length=40, blank=True)
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "pictograma del material"
        verbose_name_plural = "pictogramas del material"

    @property
    def text(self):
        return self.label or self.pictogram.label


YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_youtube_id(value):
    if value and not YOUTUBE_ID.match(value):
        raise ValidationError("Escriba solo el identificador de 11 caracteres del video de YouTube.")


class Video(ModeratedContent):
    TYPE_LABEL = "Recurso audiovisual"

    publisher = models.CharField("institución o canal que lo publica", max_length=200)
    url = models.URLField("enlace oficial", blank=True)
    youtube_id = models.CharField("identificador de YouTube (para insertar)", max_length=11, blank=True,
                                  validators=[validate_youtube_id])
    language = models.CharField("idioma", max_length=40, default="Español")
    duration = models.CharField("duración", max_length=40, blank=True)
    has_subtitles = models.BooleanField("tiene subtítulos", default=False)
    why_recommended = models.TextField("por qué se recomienda")
    audience = models.CharField("público", max_length=10, choices=Audience.choices, default=Audience.BOTH)
    reviewed_on = models.DateField("revisado el", null=True, blank=True)
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="videos")

    class Meta(ModeratedContent.Meta):
        ordering = ["-featured", "title"]
        verbose_name = "recurso audiovisual"
        verbose_name_plural = "recursos audiovisuales"

    def get_absolute_url(self):
        return reverse("practice:video", args=[self.pk])

    def publication_problems(self):
        problems = []
        if not (self.url or self.youtube_id):
            problems.append("El recurso no tiene enlace ni video insertable.")
        if not self.reviewed_on:
            problems.append("Indique la fecha en que el equipo revisó el contenido del video.")
        return problems

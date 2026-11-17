from django.db import models
from django.urls import reverse

from apps.core.models import ModeratedContent, Source, Topic
from apps.core.validators import validate_upload


class Capsule(ModeratedContent):
    """
    Cápsula educativa del Área 1 «Comprender el autismo», con estructura fija de 10 partes:
    título, introducción, explicación, importancia, ejemplos cotidianos, recurso relacionado,
    material visual, recomendaciones y precauciones, fuentes y fecha de revisión.
    """
    TYPE_LABEL = "Cápsula educativa"

    class Theme(models.TextChoices):
        WHAT = "que-es", "Qué es el autismo"
        DIVERSITY = "diversidad", "Diversidad y necesidades de apoyo"
        COMMUNICATION = "comunicacion", "Comunicación e interacción social"
        ROUTINES = "rutinas", "Rutinas y anticipación"
        EMOTIONS = "emociones", "Emociones y sensorialidad"
        MYTHS = "mitos", "Mitos y realidades"
        INCLUSION = "inclusion", "Inclusión educativa"
        RIGHTS = "derechos", "Derechos"
        HELP = "ayuda", "Buscar orientación profesional"

    class Visual(models.TextChoices):
        NONE = "", "Sin visual integrado (usar imagen o mostrar pendiente)"
        WHAT = "que_es", "Diagrama: dos áreas principales"
        PROFILE = "perfil", "Gráfico: perfiles de fortalezas y apoyos"
        COMMUNICATION = "comunicacion", "Infografía: formas de comunicarse"
        ROUTINE = "rutina", "Secuencia ilustrada de una rutina"
        EMOTIONS = "emociones", "Diagrama: señales y estrategias de calma"
        MYTHS = "mitos", "Comparativo: mitos y realidades"
        INCLUSION = "inclusion", "Diagrama: familia, escuela y apoyos"
        RIGHTS = "derechos", "Infografía: derechos y dónde están escritos"
        HELP = "ayuda", "Ruta: de la preocupación a la orientación"

    class Action(models.TextChoices):
        NONE = "", "Ninguna"
        AGENDA = "agenda", "Abrir el creador de agendas visuales"
        PICTOGRAMS = "pictogramas", "Ver el banco de pictogramas"
        DIRECTORY = "directorio", "Consultar el directorio de instituciones"
        LEGAL = "legal", "Leer las normas oficiales citadas"
        CLASSROOM = "aula", "Ver actividades y adaptaciones para el aula"
        INTERVIEWS = "entrevistas", "Ver las entrevistas"

    ACTION_TARGETS = {
        "agenda": ("practice:agenda", ""),
        "pictogramas": ("practice:pictograms", ""),
        "directorio": ("directory:index", ""),
        "legal": ("core:sources", "?tipo=legal"),
        "aula": ("practice:activities", "?lugar=escuela"),
        "entrevistas": ("interviews:index", ""),
    }

    theme = models.CharField("tema de la cápsula", max_length=20, choices=Theme.choices, db_index=True)
    order = models.PositiveSmallIntegerField("orden", default=0)
    explanation = models.TextField("explicación del tema", help_text="Separe los párrafos con una línea en blanco.")
    importance = models.TextField("importancia para familias y docentes")
    examples = models.TextField("ejemplos de situaciones cotidianas", help_text="Un ejemplo por línea.")
    practice_intro = models.TextField("cómo llevarlo a la práctica",
                                      help_text="Texto que conecta la explicación con los recursos relacionados.")
    related_activities = models.ManyToManyField("practice.Activity", verbose_name="actividades relacionadas",
                                                blank=True, related_name="capsules")
    related_materials = models.ManyToManyField("practice.Material", verbose_name="materiales relacionados",
                                               blank=True, related_name="capsules")
    related_videos = models.ManyToManyField("practice.Video", verbose_name="videos relacionados", blank=True,
                                            related_name="capsules")
    action = models.CharField("acción directa adicional", max_length=20, choices=Action.choices, blank=True)
    visual = models.CharField("visual integrado", max_length=20, choices=Visual.choices, blank=True)
    visual_image = models.ImageField("imagen propia (opcional)", upload_to="capsulas/", blank=True,
                                     validators=[validate_upload])
    visual_alt = models.CharField("texto alternativo de la imagen", max_length=250, blank=True)
    visual_caption = models.CharField("leyenda del visual", max_length=250, blank=True)
    recommendations = models.TextField("recomendaciones", help_text="Una por línea.")
    precautions = models.TextField("precauciones", help_text="Una por línea.")
    sources = models.ManyToManyField(Source, verbose_name="fuentes", related_name="capsules")
    revised_on = models.DateField("fecha de revisión")
    professional_review = models.CharField("revisión profesional", max_length=200, blank=True,
                                           help_text="Nombre y profesión de quien revisó. Vacío = pendiente.")
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="capsules")

    class Meta(ModeratedContent.Meta):
        ordering = ["order", "title"]
        verbose_name = "cápsula educativa"
        verbose_name_plural = "cápsulas educativas"

    def get_absolute_url(self):
        return reverse("learn:capsule", args=[self.pk])

    @property
    def action_url(self):
        if self.action not in self.ACTION_TARGETS:
            return ""
        name, query = self.ACTION_TARGETS[self.action]
        return reverse(name) + query

    def has_practical_resource(self):
        if not self.pk:
            return False
        return (self.related_activities.public().exists() or self.related_materials.public().exists()
                or self.related_videos.public().exists() or bool(self.action))

    def publication_problems(self):
        problems = []
        if self.pk and not self.sources.exists():
            problems.append("La cápsula no tiene fuentes bibliográficas.")
        if not self.has_practical_resource():
            problems.append("La cápsula no está conectada con ninguna actividad, material o recurso práctico publicado.")
        if self.visual_image and not self.visual_alt:
            problems.append("La imagen propia necesita un texto alternativo.")
        return problems


class FAQ(models.Model):
    question = models.CharField("pregunta", max_length=250)
    answer = models.TextField("respuesta")
    link_label = models.CharField("texto del enlace para ampliar", max_length=80, blank=True)
    link_url = models.CharField("enlace para ampliar", max_length=300, blank=True,
                                help_text="Ruta interna (/comprender/...) o URL oficial.")
    order = models.PositiveSmallIntegerField("orden", default=0)
    published = models.BooleanField("publicada", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "pregunta frecuente"
        verbose_name_plural = "preguntas frecuentes"

    def __str__(self):
        return self.question

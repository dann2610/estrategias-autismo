from django.db import models
from django.urls import reverse

from apps.core.models import ModeratedContent, Topic
from apps.core.validators import upload_path, validate_upload
from apps.practice.models import validate_youtube_id


class Interview(ModeratedContent):
    """
    Entrevista con una organización colaboradora. Mientras no se realice, se muestra como
    «Contenido próximamente» con la guía de preguntas. Nunca se publican declaraciones inventadas:
    publicar exige entrevista real, datos verificados y autorización.
    """
    TYPE_LABEL = "Entrevista"
    PRIVATE_FILE_FIELDS = ("authorization_document",)

    organization_name = models.CharField("organización", max_length=200, blank=True)
    organization_description = models.TextField("descripción institucional verificada", blank=True)
    organization_source = models.URLField("fuente de la descripción", blank=True)
    interviewee_name = models.CharField("nombre de la persona entrevistada", max_length=150, blank=True)
    interviewee_role = models.CharField("cargo", max_length=150, blank=True)
    interview_date = models.DateField("fecha de la entrevista", null=True, blank=True)
    youtube_id = models.CharField("video en YouTube (identificador)", max_length=11, blank=True,
                                  validators=[validate_youtube_id])
    media_url = models.URLField("enlace al video o audio", blank=True)
    summary = models.TextField("resumen de los temas tratados", blank=True)
    transcript = models.TextField("transcripción", blank=True)
    references = models.TextField("referencias complementarias", blank=True, help_text="Una por línea.")
    authorization_confirmed = models.BooleanField("se cuenta con autorización escrita para publicar", default=False)
    authorization_document = models.FileField("documento de autorización (privado)", upload_to=upload_path,
                                              blank=True, validators=[validate_upload])
    show_as_upcoming = models.BooleanField("mostrar como «próximamente» mientras se prepara", default=True)
    topics = models.ManyToManyField(Topic, verbose_name="temas", blank=True, related_name="interviews")

    class Meta(ModeratedContent.Meta):
        verbose_name = "entrevista"
        verbose_name_plural = "entrevistas"

    def get_absolute_url(self):
        return reverse("interviews:detail", args=[self.pk])

    def publication_problems(self):
        problems = []
        required = {"organization_name": "organización", "organization_description": "descripción institucional",
                    "interviewee_name": "nombre de la persona entrevistada", "interviewee_role": "cargo",
                    "summary": "resumen"}
        for field, label in required.items():
            if not getattr(self, field).strip():
                problems.append(f"Falta: {label}.")
        if not self.interview_date:
            problems.append("Falta la fecha de la entrevista.")
        if not (self.youtube_id or self.media_url or self.transcript.strip()):
            problems.append("Agregue el video, el audio o la transcripción.")
        if not self.authorization_confirmed:
            problems.append("Confirme que existe autorización para publicar la entrevista.")
        if self.pk and self.questions.filter(answer="").exists():
            problems.append("Hay preguntas sin respuesta; elimínelas o complete la respuesta textual.")
        return problems


class InterviewQuestion(models.Model):
    class Theme(models.TextChoices):
        NEEDS = "necesidades", "Necesidades de las familias"
        RESOURCES = "recursos", "Recursos educativos"
        INCLUSION = "inclusion", "Inclusión"
        GUIDANCE = "orientacion", "Orientación"
        DAILY = "cotidiano", "Dificultades cotidianas"

    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="questions")
    theme = models.CharField("tema", max_length=15, choices=Theme.choices)
    question = models.CharField("pregunta", max_length=300)
    answer = models.TextField("respuesta (textual, tal como se dijo)", blank=True)
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"

    def __str__(self):
        return self.question

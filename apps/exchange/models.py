from django.db import models
from django.urls import reverse

from apps.core.choices import PROVINCE_CHOICES
from apps.core.models import ModeratedContent


class ExchangeItem(ModeratedContent):
    """Intercambio de materiales educativos y de apoyo entre usuarios. Voluntario y moderado."""
    TYPE_LABEL = "Publicación de intercambio"

    class Offer(models.TextChoices):
        OFFER = "ofrezco", "Ofrezco para intercambiar o prestar"
        SEEK = "busco", "Busco"

    class ItemKind(models.TextChoices):
        BOOK = "libro", "Libro o cuento"
        GAME = "juego", "Juego educativo"
        VISUAL = "visual", "Material visual (pictogramas, agendas)"
        SENSORY = "sensorial", "Material sensorial seguro"
        OTHER = "otro", "Otro material de apoyo"

    class Condition(models.TextChoices):
        NEW = "nuevo", "Nuevo"
        GOOD = "bueno", "Buen estado"
        USED = "usado", "Usado con detalles"
        NA = "na", "No aplica"

    class Availability(models.TextChoices):
        AVAILABLE = "disponible", "Disponible"
        RESERVED = "reservado", "Reservado"
        CLOSED = "finalizado", "Finalizado"

    offer = models.CharField("tipo de publicación", max_length=10, choices=Offer.choices)
    item_kind = models.CharField("tipo de material", max_length=10, choices=ItemKind.choices)
    condition = models.CharField("estado del material", max_length=8, choices=Condition.choices, default=Condition.GOOD)
    province = models.CharField("provincia", max_length=40, choices=PROVINCE_CHOICES, default="Guayas")
    canton = models.CharField("cantón (ubicación aproximada)", max_length=60)
    contact_authorized = models.CharField("contacto que autorizas mostrar", max_length=150,
                                          help_text="Un correo o número de WhatsApp. Nunca tu domicilio.")
    delivery_terms = models.CharField("condiciones de entrega", max_length=200, blank=True,
                                      help_text="Recomendamos un lugar público y de día.")
    availability = models.CharField("disponibilidad", max_length=12, choices=Availability.choices,
                                    default=Availability.AVAILABLE, db_index=True)
    safety_confirmed = models.BooleanField("el material es seguro, está limpio y es apto para niñas y niños",
                                           default=False)

    class Meta(ModeratedContent.Meta):
        verbose_name = "publicación de intercambio"
        verbose_name_plural = "intercambio de materiales"

    def get_absolute_url(self):
        return reverse("exchange:detail", args=[self.pk])

    def publication_problems(self):
        return [] if self.safety_confirmed or self.offer == self.Offer.SEEK else [
            "Falta la confirmación de seguridad del material."]

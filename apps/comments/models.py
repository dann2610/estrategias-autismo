from django.db import models

from apps.core.models import ModeratedContent


class Comment(ModeratedContent):
    """Comentario o pregunta sobre una cápsula. Siempre se revisa antes de publicarse."""
    TYPE_LABEL = "Comentario"

    capsule = models.ForeignKey("learn.Capsule", on_delete=models.CASCADE, related_name="comments",
                                verbose_name="cápsula")

    class Meta(ModeratedContent.Meta):
        ordering = ["created_at"]
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"

    def get_absolute_url(self):
        return self.capsule.get_absolute_url() + f"#comentario-{self.pk}"

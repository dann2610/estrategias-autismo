from django.contrib import admin

from apps.core.admin_base import ModeratedAdmin

from .models import FAQ, Capsule


@admin.register(Capsule)
class CapsuleAdmin(ModeratedAdmin):
    list_display = ("title", "theme", "order", "status", "revised_on", "professional_review", "featured")
    list_filter = ("status", "theme", "featured")
    list_editable = ("order",)
    filter_horizontal = ("related_activities", "related_materials", "related_videos", "sources", "topics")
    fieldsets = (
        ("1–2. Título e introducción", {"fields": ("title", "description", "theme", "order", "topics")}),
        ("3–5. Explicación, importancia y ejemplos", {"fields": ("explanation", "importance", "examples")}),
        ("6. De la explicación a la práctica", {"fields": ("practice_intro", "related_activities",
                                                           "related_materials", "related_videos", "action")}),
        ("7. Material visual", {"fields": ("visual", "visual_image", "visual_alt", "visual_caption")}),
        ("8. Recomendaciones y precauciones", {"fields": ("recommendations", "precautions")}),
        ("9–10. Fuentes y revisión", {"fields": ("sources", "revised_on", "professional_review")}),
        ("Publicación", {"fields": ("publication_check", "status", "featured", "author", "reviewed_by",
                                    "reviewed_at", "created_at", "updated_at", "view_count")}),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "published")
    list_editable = ("order", "published")

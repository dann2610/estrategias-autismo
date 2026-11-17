"""Base de Django Admin para contenido moderado: filtros, búsqueda, acciones y registro de cambios."""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.core.choices import Status
from apps.moderation.models import ModerationAction
from apps.moderation.services import admin_edited, record, transition


class ModeratedAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "origin", "author", "featured", "updated_at")
    list_filter = ("status", "origin", "featured", "created_at")
    search_fields = ("title", "description", "author__email")
    readonly_fields = ("status", "author", "created_at", "updated_at", "submitted_at", "reviewed_by", "reviewed_at",
                       "view_count", "publication_check")

    @admin.display(description="¿Se puede publicar?")
    def publication_check(self, obj):
        if not obj or not obj.pk:
            return "Guarde primero."
        problems = obj.publication_problems()
        return "Sí, cumple los requisitos." if not problems else "No: " + " ".join(problems)
    list_per_page = 30
    date_hierarchy = "created_at"
    actions = ["approve_selected", "archive_selected"]

    def save_model(self, request, obj, form, change):
        new = obj.pk is None
        if new:
            obj.author = None  # contenido editorial creado por el equipo
        super().save_model(request, obj, form, change)
        if new:
            record(obj, request.user, ModerationAction.Action.CREATE, "", obj.status, "Creado desde administración")
        elif form.changed_data:
            admin_edited(obj, request.user, list(form.changed_data), request)

    def _bulk(self, request, queryset, action):
        ok = 0
        for obj in queryset:
            try:
                transition(obj, request.user, action, request=request)
                ok += 1
            except ValidationError as exc:
                self.message_user(request, f"«{obj}»: " + " ".join(exc.messages), messages.WARNING)
        self.message_user(request, f"{ok} elemento(s) actualizados.", messages.SUCCESS)

    @admin.action(description="Aprobar y publicar seleccionados")
    def approve_selected(self, request, queryset):
        self._bulk(request, queryset.exclude(status=Status.APPROVED), ModerationAction.Action.APPROVE)

    @admin.action(description="Archivar seleccionados")
    def archive_selected(self, request, queryset):
        self._bulk(request, queryset.exclude(status=Status.ARCHIVED), ModerationAction.Action.ARCHIVE)

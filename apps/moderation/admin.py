from django.contrib import admin

from .models import AuditLog, ModerationAction


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ModerationAction)
class ModerationActionAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "action", "content_type", "object_id", "actor", "from_status", "to_status")
    list_filter = ("action", "content_type")


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "action", "target", "actor")
    list_filter = ("action",)
    search_fields = ("target", "actor__email")

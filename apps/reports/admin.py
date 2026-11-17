from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "reason", "state", "reporter", "content_type", "object_id")
    list_filter = ("state", "reason")
    readonly_fields = ("reporter", "content_type", "object_id", "created_at")

from django.contrib import admin

from apps.core.admin_base import ModeratedAdmin

from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(ModeratedAdmin):
    list_display = ("title", "kind", "canton", "province", "verification_basis", "last_reviewed", "status")
    list_filter = ("status", "kind", "verification_basis", "province", "cost")
    search_fields = ("title", "canton", "services", "author__email")
    filter_horizontal = ("topics",)

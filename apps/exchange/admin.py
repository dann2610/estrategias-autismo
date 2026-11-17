from django.contrib import admin

from apps.core.admin_base import ModeratedAdmin

from .models import ExchangeItem


@admin.register(ExchangeItem)
class ExchangeAdmin(ModeratedAdmin):
    list_display = ("title", "offer", "item_kind", "canton", "availability", "status", "author")
    list_filter = ("status", "offer", "item_kind", "availability", "province")

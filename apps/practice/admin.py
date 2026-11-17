from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import ModeratedAdmin

from .models import Activity, Material, MaterialItem, Pictogram, Video


@admin.register(Pictogram)
class PictogramAdmin(admin.ModelAdmin):
    list_display = ("preview", "label", "category", "code", "active", "order")
    list_display_links = ("label",)
    list_filter = ("category", "active")
    list_editable = ("active", "order")
    search_fields = ("label", "code")

    @admin.display(description="Vista")
    def preview(self, obj):
        return format_html('<img src="{}" alt="" width="36" height="36">', obj.src)


@admin.register(Activity)
class ActivityAdmin(ModeratedAdmin):
    list_display = ("title", "kind", "age_range", "place", "status", "featured")
    list_filter = ("status", "kind", "age_range", "place", "featured")
    filter_horizontal = ("related_materials", "topics", "sources")


class MaterialItemInline(admin.TabularInline):
    model = MaterialItem
    extra = 1
    autocomplete_fields = ("pictogram",)


@admin.register(Material)
class MaterialAdmin(ModeratedAdmin):
    list_display = ("title", "kind", "layout", "audience", "status", "origin", "author")
    list_filter = ("status", "kind", "layout", "audience", "origin")
    filter_horizontal = ("topics",)
    inlines = [MaterialItemInline]


PictogramAdmin.search_fields = ("label", "code")


@admin.register(Video)
class VideoAdmin(ModeratedAdmin):
    list_display = ("title", "publisher", "language", "has_subtitles", "reviewed_on", "status")
    list_filter = ("status", "audience", "has_subtitles")
    filter_horizontal = ("topics",)

from django.contrib import admin

from apps.core.admin_base import ModeratedAdmin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(ModeratedAdmin):
    list_display = ("title", "capsule", "status", "author", "created_at")
    raw_id_fields = ("capsule",)

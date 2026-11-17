from django.contrib import admin

from apps.core.admin_base import ModeratedAdmin

from .models import Interview, InterviewQuestion


class QuestionInline(admin.StackedInline):
    model = InterviewQuestion
    extra = 1


@admin.register(Interview)
class InterviewAdmin(ModeratedAdmin):
    list_display = ("title", "organization_name", "interview_date", "authorization_confirmed", "status")
    list_filter = ("status", "authorization_confirmed", "show_as_upcoming")
    filter_horizontal = ("topics",)
    inlines = [QuestionInline]

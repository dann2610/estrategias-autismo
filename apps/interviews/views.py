from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.core.listing import detail
from apps.core.permissions import is_moderator

from .models import Interview


def index(request):
    return render(request, "interviews/index.html", {
        "published": Interview.objects.public().order_by("-interview_date"),
        "upcoming": Interview.objects.exclude(status="aprobado").filter(show_as_upcoming=True),
    })


def interview(request, pk):
    obj = get_object_or_404(Interview, pk=pk)
    if obj.is_public or is_moderator(request.user):
        return detail(request, Interview, pk, "interviews/detail.html",
                      extra=lambda o: {"questions": o.questions.all()})
    if obj.show_as_upcoming:
        # Página de preparación editorial: solo la guía de preguntas, sin respuestas ni datos no verificados
        return render(request, "interviews/upcoming.html", {"obj": obj, "questions": obj.questions.all()})
    raise Http404

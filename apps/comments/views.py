from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.contributions.forms import CommentForm
from apps.core.choices import Origin, Status
from apps.core.models import SiteConfig
from apps.core.ratelimit import ratelimit
from apps.learn.models import Capsule
from apps.moderation.models import ModerationAction
from apps.moderation.services import record, transition


@login_required
@require_POST
@ratelimit("comment", limit=5, period=600)
def add(request, pk):
    capsule = get_object_or_404(Capsule.objects.public(), pk=pk)
    target = capsule.get_absolute_url() + "#comentarios"
    if not SiteConfig.load().allow_comments:
        messages.error(request, "Los comentarios están desactivados temporalmente.")
        return redirect(target)
    form = CommentForm(request.POST)
    if not form.is_valid():
        errors = " ".join(e for errs in form.errors.values() for e in errs)
        messages.error(request, f"No pudimos enviar tu comentario. {errors}")
        return redirect(target)
    c = form.save(commit=False)
    c.capsule = capsule
    c.author = request.user
    c.title = f"Comentario en «{capsule.title[:150]}»"
    c.origin = Origin.COMMUNITY
    c.status = Status.DRAFT
    c.save()
    record(c, request.user, ModerationAction.Action.CREATE, "", Status.DRAFT)
    transition(c, request.user, ModerationAction.Action.SUBMIT, request=request)
    messages.success(request, "Gracias. Tu comentario se publicará después de ser revisado.")
    return redirect(target)

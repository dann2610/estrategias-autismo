from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.choices import Origin, Status
from apps.core.models import SiteConfig
from apps.core.permissions import get_owned_object_or_404
from apps.core.ratelimit import ratelimit
from apps.directory.models import Institution
from apps.moderation.models import ModerationAction
from apps.moderation.services import author_edited, history_for, record, transition
from apps.practice.models import Material

from .registry import TYPES, TYPES_BY_SLUG, get_moderated_model, type_for_object, user_contributions


def available_types():
    if SiteConfig.load().allow_exchange:
        return TYPES
    return [t for t in TYPES if t.slug != "intercambio"]


def index(request):
    return render(request, "contributions/index.html", {"types": available_types()})


def _apply_defaults(obj, user):
    obj.author = user
    obj.status = Status.DRAFT
    obj.origin = Origin.COMMUNITY
    if isinstance(obj, Material):
        obj.layout = Material.Layout.FILE
    if isinstance(obj, Institution):
        obj.origin = Origin.PENDING_CHECK
        obj.verification_basis = Institution.Basis.PENDING
        obj.services = obj.services or "Por verificar"


@login_required
@ratelimit("contribution", limit=15, period=3600)
def create(request, type_slug):
    ctype = {t.slug: t for t in available_types()}.get(type_slug)
    if not ctype:
        raise Http404
    form = ctype.form_class(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        _apply_defaults(obj, request.user)
        obj.save()
        form.save_m2m()
        record(obj, request.user, ModerationAction.Action.CREATE, "", Status.DRAFT)
        messages.info(request, "Guardamos tu borrador. Revisa el resumen y envíalo a revisión.")
        return redirect("contributions:summary", obj.model_key, obj.pk)
    return render(request, "contributions/form.html", {"form": form, "ctype": ctype})


def _owned(request, model_key, pk):
    model = get_moderated_model(model_key)
    if not model:
        raise Http404
    return get_owned_object_or_404(model, request.user, pk=pk)


@login_required
def summary(request, model_key, pk):
    obj = _owned(request, model_key, pk)
    ctype = type_for_object(obj)
    rows = []
    if ctype:
        form = ctype.form_class(instance=obj)
        for name in form.Meta.fields:
            value = getattr(obj, f"get_{name}_display", lambda n=name: getattr(obj, n))()
            if name == "file":
                value = "Archivo adjunto" if value else ""
            rows.append((form.fields[name].label, value))
    else:
        rows.append(("Texto", obj.description))
    return render(request, "contributions/summary.html", {
        "obj": obj, "ctype": ctype, "rows": rows, "history": history_for(obj)})


@login_required
@ratelimit("contribution_edit", limit=30, period=3600)
def edit(request, model_key, pk):
    obj = _owned(request, model_key, pk)
    ctype = type_for_object(obj)
    if not ctype or not obj.author_can_edit:
        messages.warning(request, "Este aporte no puede editarse en su estado actual.")
        return redirect("contributions:summary", model_key, pk)
    form = ctype.form_class(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        changed = list(form.changed_data)
        was_public = obj.status == Status.APPROVED
        obj = form.save(commit=False)
        obj.author = request.user  # la autoría no se puede reasignar
        obj.save()
        form.save_m2m()
        author_edited(obj, request.user, changed)
        if was_public:
            messages.info(request, "Tus cambios volvieron a revisión. Mientras tanto, el aporte no se muestra.")
        else:
            messages.success(request, "Cambios guardados.")
        return redirect("contributions:summary", model_key, pk)
    return render(request, "contributions/form.html", {"form": form, "ctype": ctype, "obj": obj})


AUTHOR_ACTIONS = {
    "enviar": ModerationAction.Action.SUBMIT,
    "reenviar": ModerationAction.Action.RESUBMIT,
    "retirar": ModerationAction.Action.WITHDRAW,
}


@login_required
@require_POST
def act(request, model_key, pk, action):
    obj = _owned(request, model_key, pk)
    if action not in AUTHOR_ACTIONS:
        raise Http404
    try:
        transition(obj, request.user, AUTHOR_ACTIONS[action], request=request)
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
    else:
        if action in ("enviar", "reenviar"):
            messages.success(request, "Gracias. Tu aporte quedó pendiente de revisión; te avisaremos cuando se revise.")
        else:
            messages.info(request, "Retiraste tu aporte. Ya no es visible públicamente.")
    return redirect("contributions:summary", model_key, pk)


@login_required
def mine(request):
    status = request.GET.get("estado") or None
    if status and status not in Status.values:
        status = None
    return render(request, "contributions/mine.html", {
        "items": user_contributions(request.user, status), "statuses": Status.choices, "current": status})

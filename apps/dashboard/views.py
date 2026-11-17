from datetime import timedelta
from itertools import chain

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.contributions.registry import MODERATED_MODEL_KEYS, get_moderated_model, moderated_models
from apps.core.choices import Status
from apps.core.permissions import can_manage_users, can_view_stats, is_moderator
from apps.moderation.models import AuditLog, ModerationAction
from apps.moderation.services import audit, history_for, transition
from apps.notifications.services import notify
from apps.directory.models import Institution
from apps.interviews.models import Interview
from apps.learn.models import Capsule
from apps.practice.models import Activity, Material
from apps.reports.models import Report

User = get_user_model()
A = ModerationAction.Action

INTERNAL_FIELDS = {"id", "author", "reviewed_by", "reviewed_at", "review_comment", "status", "created_at",
                   "updated_at", "submitted_at", "view_count", "featured"}


def require(check):
    def decorator(view):
        @login_required
        def wrapped(request, *args, **kwargs):
            if not check(request.user):
                raise PermissionDenied("No tienes permiso para acceder al panel.")
            return view(request, *args, **kwargs)
        wrapped.__name__ = view.__name__
        return wrapped
    return decorator


moderator_required = require(is_moderator)


def _status_counts():
    totals = {s: 0 for s in Status.values}
    for model in moderated_models():
        for row in model.objects.values("status").annotate(n=Count("id")):
            totals[row["status"]] += row["n"]
    return totals


@moderator_required
def home(request):
    totals = _status_counts()
    pending = sorted(chain(*[m.objects.filter(status__in=[Status.PENDING, Status.IN_REVIEW]) for m in moderated_models()]),
                     key=lambda o: o.submitted_at or o.created_at)[:8]
    return render(request, "dashboard/home.html", {
        "kpis": [
            ("Propuestas pendientes", totals[Status.PENDING] + totals[Status.IN_REVIEW], "hourglass-split", "warning"),
            ("Aprobadas / publicadas", totals[Status.APPROVED], "check-circle", "success"),
            ("Rechazadas", totals[Status.REJECTED], "x-circle", "danger"),
            ("Reportes sin resolver", Report.objects.filter(state=Report.State.OPEN).count(), "flag", "danger"),
            ("Actividades y materiales publicados", Activity.objects.public().count() + Material.objects.public().count(), "collection", "primary"),
            ("Usuarios registrados", User.objects.count(), "people", "info"),
        ],
        "pending": pending,
        "quality_count": len(quality_issues()),
        "recent_actions": ModerationAction.objects.select_related("actor", "content_type")[:8],
    })


@moderator_required
def inbox(request):
    status = request.GET.get("estado") or "pendientes"
    model_key = request.GET.get("tipo") or ""
    author = (request.GET.get("autor") or "").strip()
    since = parse_date(request.GET.get("desde") or "")
    models = [get_moderated_model(model_key)] if model_key in MODERATED_MODEL_KEYS else moderated_models()
    items = []
    for model in models:
        qs = model.objects.select_related("author")
        if status == "pendientes":
            qs = qs.filter(status__in=[Status.PENDING, Status.IN_REVIEW])
        elif status in Status.values:
            qs = qs.filter(status=status)
        if author:
            qs = qs.filter(author__email__icontains=author)
        if since:
            qs = qs.filter(created_at__date__gte=since)
        items.append(qs)
    items = sorted(chain(*items), key=lambda o: o.submitted_at or o.created_at, reverse=(status != "pendientes"))
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    types = [(k, get_moderated_model(k)._meta.verbose_name.capitalize()) for k in MODERATED_MODEL_KEYS]
    return render(request, "dashboard/inbox.html", {
        "page_obj": page, "types": types, "statuses": Status.choices, "status": status, "model_key": model_key,
        "author": author, "since": request.GET.get("desde", ""), "querystring": params.urlencode()})


def _get(model_key, pk):
    model = get_moderated_model(model_key)
    if not model:
        raise Http404
    return get_object_or_404(model, pk=pk)


def _field_rows(obj):
    rows = []
    for f in obj._meta.get_fields():
        if not getattr(f, "concrete", False) or f.name in INTERNAL_FIELDS or f.many_to_many:
            continue
        value = getattr(obj, f"get_{f.name}_display")() if getattr(f, "choices", None) else getattr(obj, f.name)
        is_file = f.get_internal_type() == "FileField"
        if value in (None, "") or (is_file and not value):
            continue
        if is_file:
            value = reverse("core:file", args=[obj.model_key, obj.pk, f.name])
        rows.append({"label": f.verbose_name.capitalize(), "value": value, "is_file": is_file,
                     "is_url": f.get_internal_type() == "URLField", "private": f.name in obj.PRIVATE_FILE_FIELDS})
    for f in obj._meta.many_to_many:
        vals = ", ".join(str(v) for v in getattr(obj, f.name).all())
        if vals and f.name != "helpful_by":
            rows.append({"label": f.verbose_name.capitalize(), "value": vals})
    return rows


@moderator_required
def review(request, model_key, pk):
    obj = _get(model_key, pk)
    return render(request, "dashboard/review.html", {
        "obj": obj, "rows": _field_rows(obj), "history": history_for(obj),
        "admin_url": reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk]),
        "reports": Report.objects.filter(content_type__app_label=obj._meta.app_label,
                                         content_type__model=obj._meta.model_name, object_id=obj.pk)})


ACTIONS = {"iniciar": A.START_REVIEW, "aprobar": A.APPROVE, "rechazar": A.REJECT,
           "cambios": A.REQUEST_CHANGES, "despublicar": A.UNPUBLISH, "archivar": A.ARCHIVE}


@moderator_required
@require_POST
def act(request, model_key, pk):
    obj = _get(model_key, pk)
    action = request.POST.get("accion")
    if action == "destacar":
        obj.featured = not obj.featured
        obj.save(update_fields=["featured"])
        audit(request.user, "contenido:destacar", f"{obj.TYPE_LABEL}: {obj}", {"destacado": obj.featured}, request)
        messages.success(request, "Destacado en inicio." if obj.featured else "Ya no está destacado.")
        return redirect("dashboard:review", model_key, pk)
    if action not in ACTIONS:
        raise Http404
    try:
        transition(obj, request.user, ACTIONS[action], request.POST.get("comentario", ""), request=request)
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect("dashboard:review", model_key, pk)
    messages.success(request, f"Acción realizada: {ACTIONS[action].label}.")
    if action in ("aprobar", "rechazar", "cambios"):
        return redirect("dashboard:inbox")
    return redirect("dashboard:review", model_key, pk)


@moderator_required
def delete(request, model_key, pk):
    obj = _get(model_key, pk)
    if request.method == "POST" and request.POST.get("confirmar") == "si":
        label = f"{obj.TYPE_LABEL}: {obj}"
        audit(request.user, "contenido:eliminar", label, {"id": obj.pk, "modelo": model_key,
                                                          "motivo": request.POST.get("motivo", "")[:300]}, request)
        if obj.author_id and obj.author_id != request.user.pk:
            notify(obj.author, f"Tu contribución «{obj.title}» fue eliminada conforme a las normas de la comunidad.")
        obj.delete()
        messages.success(request, "Contenido eliminado.")
        return redirect("dashboard:inbox")
    return render(request, "dashboard/confirm_delete.html", {"obj": obj})


@moderator_required
def reports(request):
    state = request.GET.get("estado") or Report.State.OPEN
    qs = Report.objects.select_related("reporter", "content_type")
    if state in Report.State.values:
        qs = qs.filter(state=state)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/reports.html", {"page_obj": page, "state": state,
                                                      "states": Report.State.choices})


@moderator_required
@require_POST
def resolve_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    new_state = request.POST.get("estado")
    if new_state not in (Report.State.RESOLVED, Report.State.DISMISSED):
        raise Http404
    report.state = new_state
    report.resolution = request.POST.get("resolucion", "")[:1000]
    report.resolved_by = request.user
    report.resolved_at = timezone.now()
    report.save()
    audit(request.user, "reporte:" + new_state, str(report), {"id": report.pk}, request)
    if report.reporter:
        notify(report.reporter, "Gracias por tu reporte. El equipo de moderación ya lo revisó.")
    messages.success(request, "Reporte actualizado.")
    return redirect("dashboard:reports")


@require(can_manage_users)
def users(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.select_related("profile").order_by("-date_joined")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/users.html", {"page_obj": page, "q": q})


@require(can_manage_users)
@require_POST
def toggle_user(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.is_superuser or target == request.user:
        messages.error(request, "No se puede suspender esta cuenta desde el panel.")
        return redirect("dashboard:users")
    reason = request.POST.get("motivo", "").strip()
    if target.is_active and not reason:
        messages.error(request, "Indica el motivo de la suspensión.")
        return redirect("dashboard:users")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    profile = getattr(target, "profile", None)
    if profile:
        profile.suspension_reason = reason if not target.is_active else ""
        profile.save(update_fields=["suspension_reason"])
    audit(request.user, "usuario:" + ("reactivar" if target.is_active else "suspender"), target.email,
          {"motivo": reason}, request)
    messages.success(request, "Cuenta reactivada." if target.is_active else "Cuenta suspendida.")
    return redirect("dashboard:users")


@require(can_view_stats)
def stats(request):
    since = timezone.now() - timedelta(days=30)
    per_type = []
    top = []
    for model in moderated_models():
        agg = model.objects.aggregate(total=Count("id"), visitas=Sum("view_count"))
        per_type.append({"label": model._meta.verbose_name_plural.capitalize(), "total": agg["total"],
                         "publicados": model.objects.public().count(),
                         "recibidos_30d": model.objects.filter(created_at__gte=since).exclude(author=None).count(),
                         "visitas": agg["visitas"] or 0})
        top += list(model.objects.public().filter(view_count__gt=0).order_by("-view_count")[:5])
    top = sorted(top, key=lambda o: o.view_count, reverse=True)[:10]
    decisions = ModerationAction.objects.filter(created_at__gte=since).values("action").annotate(n=Count("id"))
    return render(request, "dashboard/stats.html", {
        "per_type": per_type, "top": top,
        "decisions": [(A(d["action"]).label, d["n"]) for d in decisions],
        "new_users": User.objects.filter(date_joined__gte=since).count()})


@moderator_required
def audit_log(request):
    page = Paginator(AuditLog.objects.select_related("actor"), 30).get_page(request.GET.get("page"))
    return render(request, "dashboard/audit.html", {"page_obj": page})


@moderator_required
def moderation_history(request):
    page = Paginator(ModerationAction.objects.select_related("actor", "content_type"), 30).get_page(
        request.GET.get("page"))
    return render(request, "dashboard/history.html", {"page_obj": page})


def quality_issues():
    """Revisión editorial: contenido publicado o en preparación con elementos faltantes."""
    issues = []
    stale = timezone.now().date() - timedelta(days=365)
    for c in Capsule.objects.exclude(status__in=[Status.ARCHIVED, Status.WITHDRAWN]):
        for p in c.publication_problems():
            issues.append((c, p))
        if not c.visual and not c.visual_image:
            issues.append((c, "Sin material visual: se muestra el espacio «recurso visual pendiente»."))
        if not c.professional_review:
            issues.append((c, "Pendiente de revisión por un profesional."))
    for i in Institution.objects.public():
        if i.last_reviewed and i.last_reviewed < stale:
            issues.append((i, "La información tiene más de un año sin revisarse."))
    for iv in Interview.objects.exclude(status=Status.APPROVED):
        issues.append((iv, "Entrevista en preparación: " + (" ".join(iv.publication_problems()) or "lista para revisión.")))
    return issues


@moderator_required
def quality(request):
    return render(request, "dashboard/quality.html", {"issues": quality_issues()})

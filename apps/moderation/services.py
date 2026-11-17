"""
Único punto de cambio de estado del contenido moderado.

Principio: la comunidad propone, el administrador revisa y la plataforma comparte
contenido aprobado. Cada transición se valida según quién la realiza, se guarda en
el historial y se notifica al autor.
"""
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.choices import Status
from apps.core.permissions import is_moderator

from .models import AuditLog, ModerationAction

A = ModerationAction.Action
S = Status

# acción: (estados de origen permitidos, estado destino, ¿requiere moderador?)
TRANSITIONS = {
    A.SUBMIT: ({S.DRAFT, S.CHANGES}, S.PENDING, False),
    A.RESUBMIT: ({S.REJECTED, S.WITHDRAWN, S.CHANGES}, S.PENDING, False),
    A.WITHDRAW: ({S.DRAFT, S.PENDING, S.CHANGES, S.APPROVED, S.REJECTED}, S.WITHDRAWN, False),
    A.START_REVIEW: ({S.PENDING}, S.IN_REVIEW, True),
    A.APPROVE: ({S.PENDING, S.IN_REVIEW, S.CHANGES, S.ARCHIVED}, S.APPROVED, True),
    A.REJECT: ({S.PENDING, S.IN_REVIEW}, S.REJECTED, True),
    A.REQUEST_CHANGES: ({S.PENDING, S.IN_REVIEW}, S.CHANGES, True),
    A.UNPUBLISH: ({S.APPROVED}, S.IN_REVIEW, True),
    A.ARCHIVE: ({S.APPROVED, S.REJECTED, S.WITHDRAWN, S.PENDING, S.IN_REVIEW, S.CHANGES}, S.ARCHIVED, True),
}

NEEDS_COMMENT = {A.REJECT, A.REQUEST_CHANGES}

AUTHOR_MESSAGES = {
    A.APPROVE: "Tu aporte «{t}» fue aprobado y ya está publicado. ¡Gracias por compartirlo!",
    A.REJECT: "Tu aporte «{t}» no fue aprobado. Motivo: {c}",
    A.REQUEST_CHANGES: "Se solicitaron cambios en «{t}»: {c}",
    A.UNPUBLISH: "Tu aporte «{t}» fue retirado temporalmente de la vista pública para revisión.",
    A.ARCHIVE: "Tu aporte «{t}» fue archivado.",
    A.START_REVIEW: "Tu aporte «{t}» está en revisión.",
}


def record(obj, actor, action, from_status="", to_status="", comment="", changes=None):
    return ModerationAction.objects.create(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk, actor=actor,
        action=action, from_status=from_status, to_status=to_status, comment=comment,
        changes=changes or {},
    )


def audit(actor, action, target="", details=None, request=None):
    ip = request.META.get("REMOTE_ADDR") if request else None
    return AuditLog.objects.create(actor=actor, action=action, target=str(target)[:255],
                                   details=details or {}, ip_address=ip)


def history_for(obj):
    return ModerationAction.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk
    ).select_related("actor")


@transaction.atomic
def transition(obj, actor, action, comment="", request=None):
    from apps.notifications.services import notify, notify_moderators

    if action not in TRANSITIONS:
        raise ValidationError("Acción no válida.")
    sources, target, moderator_only = TRANSITIONS[action]
    moderator = is_moderator(actor)
    if moderator_only and not moderator:
        raise PermissionDenied("Solo el equipo de moderación puede realizar esta acción.")
    if not moderator_only and obj.author_id != getattr(actor, "pk", None):
        raise PermissionDenied("Solo el autor puede realizar esta acción.")
    if obj.status not in sources:
        raise ValidationError(f"No se puede «{A(action).label.lower()}» un contenido en estado "
                              f"«{obj.get_status_display()}».")
    comment = (comment or "").strip()
    if action in NEEDS_COMMENT and not comment:
        raise ValidationError("Debes escribir el motivo o los cambios solicitados.")
    if action == A.APPROVE:
        problems = obj.publication_problems()
        if problems:
            raise ValidationError(["Todavía no se puede publicar:"] + problems)

    previous = obj.status
    obj.status = target
    now = timezone.now()
    fields = ["status", "updated_at"]
    if action in (A.SUBMIT, A.RESUBMIT):
        obj.submitted_at = now
        fields.append("submitted_at")
    if moderator_only:
        obj.reviewed_by = actor
        obj.reviewed_at = now
        obj.review_comment = comment
        fields += ["reviewed_by", "reviewed_at", "review_comment"]
    obj.save(update_fields=fields)
    record(obj, actor, action, previous, target, comment)

    if moderator_only:
        audit(actor, f"moderacion:{action}", f"{obj.TYPE_LABEL}: {obj}",
              {"id": obj.pk, "modelo": obj.model_key, "de": previous, "a": target}, request)
        if obj.author_id and obj.author_id != actor.pk and action in AUTHOR_MESSAGES:
            notify(obj.author, AUTHOR_MESSAGES[action].format(t=obj.title, c=comment),
                   reverse("contributions:mine"))
    elif action in (A.SUBMIT, A.RESUBMIT):
        notify_moderators(f"Nueva propuesta pendiente: {obj.TYPE_LABEL} «{obj.title}».",
                          reverse("dashboard:review", args=[obj.model_key, obj.pk]))
    return obj


def author_edited(obj, actor, changed_fields):
    """Toda edición del autor sobre algo ya publicado o revisado vuelve a revisión."""
    previous = obj.status
    if previous in (S.APPROVED, S.IN_REVIEW, S.REJECTED, S.WITHDRAWN):
        obj.status = S.PENDING
        obj.submitted_at = timezone.now()
        obj.save(update_fields=["status", "submitted_at", "updated_at"])
        from apps.notifications.services import notify_moderators
        notify_moderators(f"Contenido modificado por su autor, requiere revisión: «{obj.title}».",
                          reverse("dashboard:review", args=[obj.model_key, obj.pk]))
    record(obj, actor, A.EDIT_AUTHOR, previous, obj.status, changes={"campos": changed_fields})


def admin_edited(obj, actor, changed_fields, request=None):
    record(obj, actor, A.EDIT_ADMIN, obj.status, obj.status, changes={"campos": changed_fields})
    audit(actor, "contenido:editar", f"{obj.TYPE_LABEL}: {obj}",
          {"id": obj.pk, "modelo": obj.model_key, "campos": changed_fields}, request)

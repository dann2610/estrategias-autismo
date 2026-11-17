"""Comprobaciones de permisos en el servidor. Las plantillas solo ocultan enlaces; la
autorización real se hace aquí."""
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

MODERATE = "moderation.moderate_content"
MANAGE_USERS = "moderation.manage_users"
VIEW_STATS = "moderation.view_statistics"


def _active(user):
    return bool(user and user.is_authenticated and user.is_active)


def is_moderator(user):
    return _active(user) and (user.is_superuser or user.has_perm(MODERATE))


def can_manage_users(user):
    return _active(user) and (user.is_superuser or user.has_perm(MANAGE_USERS))


def can_view_stats(user):
    return _active(user) and (user.is_superuser or user.has_perm(VIEW_STATS))


class PermissionRequiredMixin(AccessMixin):
    """Redirige al inicio de sesión si no hay sesión; responde 403 si no hay permiso."""
    check = staticmethod(is_moderator)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.check(request.user):
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)


class ModeratorRequiredMixin(PermissionRequiredMixin):
    check = staticmethod(is_moderator)


class UserManagerRequiredMixin(PermissionRequiredMixin):
    check = staticmethod(can_manage_users)


def get_owned_object_or_404(model, user, **lookup):
    """Devuelve el objeto solo si pertenece al usuario. Evita acceder a propuestas ajenas."""
    obj = get_object_or_404(model, **lookup)
    if getattr(obj, "author_id", None) != user.pk:
        raise PermissionDenied("Este contenido no te pertenece.")
    return obj


def get_visible_or_404(model, user, **lookup):
    """Contenido aprobado para todos; el autor y moderadores ven además lo no publicado."""
    obj = get_object_or_404(model, **lookup)
    if obj.is_public or is_moderator(user) or (user.is_authenticated and obj.author_id == user.pk):
        return obj
    from django.http import Http404
    raise Http404

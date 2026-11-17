"""Ayudantes para listados públicos con filtros, búsqueda y paginación, y fichas de detalle."""
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import render

from .models import Favorite
from .permissions import get_visible_or_404


def choice_field(label, choices, empty="Todos"):
    return forms.ChoiceField(label=label, required=False, choices=[("", empty)] + list(choices))


def filtered_list(request, queryset, filter_form_class, template, search_fields=("title", "description"),
                  extra=None, per_page=12, field_map=None):
    """Aplica los filtros del formulario (campo -> lookup) sobre contenido ya aprobado."""
    form = filter_form_class(request.GET or None)
    qs = queryset
    field_map = field_map or {}
    if form.is_valid():
        for name, value in form.cleaned_data.items():
            if value in (None, "", False):
                continue
            if name == "q":
                cond = Q()
                for f in search_fields:
                    cond |= Q(**{f"{f}__icontains": value})
                qs = qs.filter(cond)
            elif name in field_map:
                lookup = field_map[name]
                qs = lookup(qs, value) if callable(lookup) else qs.filter(**{lookup: value})
            else:
                qs = qs.filter(**{name: value})
    page = Paginator(qs, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    ctx = {"filter_form": form, "page_obj": page, "querystring": params.urlencode(),
           "total": page.paginator.count}
    ctx.update(extra or {})
    return render(request, template, ctx)


def detail(request, model, pk, template, extra=None):
    obj = get_visible_or_404(model, request.user, pk=pk)
    if obj.is_public:
        model.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
    is_fav = False
    if request.user.is_authenticated:
        is_fav = Favorite.objects.filter(user=request.user, content_type=ContentType.objects.get_for_model(model),
                                         object_id=obj.pk).exists()
    ctx = {"obj": obj, "is_favorite": is_fav}
    ctx.update(extra(obj) if callable(extra) else (extra or {}))
    return render(request, template, ctx)

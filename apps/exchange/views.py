from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.listing import choice_field, detail, filtered_list
from apps.core.models import SiteConfig
from apps.core.permissions import get_owned_object_or_404
from apps.moderation.services import audit

from .models import ExchangeItem


def _enabled():
    if not SiteConfig.load().allow_exchange:
        raise Http404


class ExchangeFilter(forms.Form):
    q = forms.CharField(label="Buscar", required=False)
    tipo = choice_field("Publicación", ExchangeItem.Offer.choices)
    material = choice_field("Material", ExchangeItem.ItemKind.choices)
    canton = forms.CharField(label="Cantón", required=False)
    finalizados = forms.BooleanField(label="Incluir finalizados", required=False)


def index(request):
    _enabled()
    qs = ExchangeItem.objects.public().order_by("-reviewed_at")
    if not request.GET.get("finalizados"):
        qs = qs.exclude(availability=ExchangeItem.Availability.CLOSED)
    return filtered_list(request, qs, ExchangeFilter, "exchange/index.html",
                         field_map={"tipo": "offer", "material": "item_kind", "canton": "canton__icontains",
                                    "finalizados": lambda q, v: q})


def item(request, pk):
    _enabled()
    return detail(request, ExchangeItem, pk, "exchange/detail.html",
                  extra=lambda o: {"is_owner": request.user.is_authenticated and o.author_id == request.user.pk,
                                   "availabilities": ExchangeItem.Availability.choices})


@login_required
@require_POST
def set_availability(request, pk):
    """El autor actualiza la disponibilidad sin volver a revisión (no cambia el contenido)."""
    obj = get_owned_object_or_404(ExchangeItem, request.user, pk=pk)
    value = request.POST.get("availability")
    if value not in ExchangeItem.Availability.values:
        raise Http404
    obj.availability = value
    obj.save(update_fields=["availability", "updated_at"])
    audit(request.user, "intercambio:disponibilidad", str(obj), {"id": obj.pk, "valor": value}, request)
    messages.success(request, f"Disponibilidad actualizada: {obj.get_availability_display()}.")
    return redirect(obj.get_absolute_url() if obj.is_public else "contributions:mine")


def rules(request):
    _enabled()
    return render(request, "exchange/rules.html")

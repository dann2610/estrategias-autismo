from django import forms

from apps.core.choices import PROVINCE_CHOICES
from apps.core.listing import choice_field, detail, filtered_list

from .models import Institution


class InstitutionFilter(forms.Form):
    q = forms.CharField(label="Buscar", required=False)
    tipo = choice_field("Tipo", Institution.Kind.choices)
    provincia = choice_field("Provincia", PROVINCE_CHOICES, "Todas")
    canton = forms.CharField(label="Cantón", required=False)
    costo = choice_field("Costo", Institution.Cost.choices, "Cualquiera")


def index(request):
    return filtered_list(
        request, Institution.objects.public().order_by("province", "canton", "title"), InstitutionFilter,
        "directory/index.html", search_fields=("title", "description", "services", "canton"),
        field_map={"tipo": "kind", "provincia": "province", "canton": "canton__icontains", "costo": "cost"},
        extra={"kinds": Institution.Kind.choices, "basis": Institution.BASIS_HELP,
               "basis_labels": dict(Institution.Basis.choices)})


def institution(request, pk):
    return detail(request, Institution, pk, "directory/detail.html")

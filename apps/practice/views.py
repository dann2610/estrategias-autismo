from django import forms
from django.shortcuts import get_object_or_404, render

from apps.core.choices import AgeRange
from apps.core.listing import choice_field, detail, filtered_list
from apps.core.permissions import get_visible_or_404

from .models import TWEMOJI_CREDIT, TWEMOJI_LICENSE, TWEMOJI_LICENSE_URL, Activity, Audience, Material, Pictogram, Video

AGES = [c for c in AgeRange.choices if c[0] != "todas"]


def hub(request):
    """Área 2: Actividades y recursos prácticos."""
    return render(request, "practice/hub.html", {
        "activities": Activity.objects.public().order_by("-featured", "title")[:6],
        "materials": Material.objects.public().filter(origin="editorial").order_by("-featured", "title")[:8],
        "videos": Video.objects.public()[:2],
        "kinds": Activity.Kind.choices,
    })


class ActivityFilter(forms.Form):
    q = forms.CharField(label="Buscar", required=False)
    tipo = choice_field("Tipo", Activity.Kind.choices)
    edad = choice_field("Edad", AGES, "Todas")
    lugar = choice_field("Lugar", [c for c in Activity.Place.choices if c[0] != "ambos"], "Cualquiera")
    duracion = choice_field("Duración", Activity.Duration.choices, "Cualquiera")


def activities(request):
    return filtered_list(
        request, Activity.objects.public().order_by("-featured", "title"), ActivityFilter, "practice/activities.html",
        search_fields=("title", "description", "objective"),
        field_map={"tipo": "kind", "duracion": "duration",
                   "edad": lambda qs, v: qs.filter(age_range__in=[v, "todas"]),
                   "lugar": lambda qs, v: qs.filter(place__in=[v, "ambos"])})


def activity(request, pk):
    return detail(request, Activity, pk, "practice/activity.html", extra=lambda o: {
        "materials": o.related_materials.public(), "capsules": o.capsules.public()})


class MaterialFilter(forms.Form):
    q = forms.CharField(label="Buscar", required=False)
    tipo = choice_field("Tipo", Material.Kind.choices)
    publico = choice_field("Público", Audience.choices)
    origen = choice_field("Origen", [("editorial", "Elaborados por el proyecto"), ("comunidad", "Compartidos por la comunidad")])


def materials(request):
    return filtered_list(request, Material.objects.public().order_by("-featured", "title"), MaterialFilter,
                         "practice/materials.html", field_map={"tipo": "kind", "publico": "audience",
                                                               "origen": "origin"})


def material(request, pk):
    return detail(request, Material, pk, "practice/material.html", extra=lambda o: {
        "items": o.items.select_related("pictogram"), "activities": o.activities.public(),
        "capsules": o.capsules.public(), "prompts": [p for p in o.worksheet_prompts.splitlines() if p.strip()]})


def material_print(request, pk):
    obj = get_visible_or_404(Material, request.user, pk=pk)
    if not obj.is_printable:
        return render(request, "practice/material.html", {"obj": obj}, status=404)
    items = list(obj.items.select_related("pictogram"))
    if obj.layout == Material.Layout.PAIRS:
        items = items + items
    return render(request, "practice/print.html", {
        "obj": obj, "items": items, "prompts": [p for p in obj.worksheet_prompts.splitlines() if p.strip()]})


def pictograms(request):
    pics = Pictogram.objects.filter(active=True)
    groups = [(label, [p for p in pics if p.category == value]) for value, label in Pictogram.Category.choices]
    return render(request, "practice/pictograms.html", {
        "groups": [g for g in groups if g[1]], "credit": TWEMOJI_CREDIT, "license": TWEMOJI_LICENSE,
        "license_url": TWEMOJI_LICENSE_URL})


def agenda(request):
    """Creador de agendas visuales: se arma en el navegador y se imprime o guarda como PDF."""
    pics = Pictogram.objects.filter(active=True)
    data = [{"id": p.pk, "label": p.label, "src": p.src, "cat": p.category} for p in pics]
    return render(request, "practice/agenda.html", {
        "pictogram_data": data, "categories": Pictogram.Category.choices, "credit": TWEMOJI_CREDIT,
        "license": TWEMOJI_LICENSE, "license_url": TWEMOJI_LICENSE_URL})


class VideoFilter(forms.Form):
    q = forms.CharField(label="Buscar", required=False)
    publico = choice_field("Público", Audience.choices)


def videos(request):
    return filtered_list(request, Video.objects.public(), VideoFilter, "practice/videos.html",
                         search_fields=("title", "description", "publisher"), field_map={"publico": "audience"})


def video(request, pk):
    return detail(request, Video, pk, "practice/video.html", extra=lambda o: {"capsules": o.capsules.public()})

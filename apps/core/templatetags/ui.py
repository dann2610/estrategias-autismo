"""Etiquetas y filtros de presentación."""
from django import forms, template
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html

from apps.core.choices import Origin, Status

register = template.Library()

# modelo -> (área, pictograma, etiqueta)
MODULES = {
    "learn.capsule": ("1", "1f4a1", "Cápsula educativa"),
    "practice.activity": ("2", "1f3a8", "Actividad"),
    "practice.material": ("2", "1f4cb", "Material"),
    "practice.video": ("3", "1f4fa", "Recurso audiovisual"),
    "directory.institution": ("3", "1f3db", "Directorio"),
    "interviews.interview": ("3", "1f399", "Entrevista"),
    "exchange.exchangeitem": ("3", "1f4e6", "Intercambio"),
    "comments.comment": ("1", "1f4ac", "Comentario"),
}

STATUS_STYLE = {
    Status.DRAFT: "secondary", Status.PENDING: "warning", Status.IN_REVIEW: "info", Status.CHANGES: "warning",
    Status.APPROVED: "success", Status.REJECTED: "danger", Status.WITHDRAWN: "secondary", Status.ARCHIVED: "dark",
}


@register.simple_tag
def picto(code):
    return static(f"picto/{code}.svg")


@register.filter
def lines(value):
    return [ln.strip(" -•\t") for ln in (value or "").splitlines() if ln.strip(" -•\t")]


@register.filter
def paragraphs(value):
    return [p.strip() for p in (value or "").split("\n\n") if p.strip()]


@register.filter
def bs(field, extra=""):
    w = field.field.widget
    if isinstance(w, forms.CheckboxInput):
        css = "form-check-input"
    elif isinstance(w, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return field.as_widget()
    elif isinstance(w, forms.Select):
        css = "form-select"
    else:
        css = "form-control"
    if field.errors:
        css += " is-invalid"
    attrs = {"class": f"{css} {extra}".strip()}
    if field.help_text:
        attrs["aria-describedby"] = f"{field.auto_id}_help"
    return field.as_widget(attrs=attrs)


@register.filter
def is_check(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_multi(field):
    return isinstance(field.field.widget, (forms.RadioSelect, forms.CheckboxSelectMultiple))


@register.simple_tag
def module(obj_or_key):
    key = obj_or_key if isinstance(obj_or_key, str) else getattr(obj_or_key, "model_key", "")
    area, code, label = MODULES.get(key, ("1", "1f4a1", ""))
    return {"area": area, "picto": static(f"picto/{code}.svg"), "label": label}


@register.filter
def status_badge(obj):
    return format_html('<span class="badge rounded-pill text-bg-{}">{}</span>',
                       STATUS_STYLE.get(obj.status, "secondary"), obj.get_status_display())


@register.simple_tag
def file_url(obj, field):
    return reverse("core:file", args=[obj.model_key, obj.pk, field])


@register.filter
def yesno_es(value):
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    return value


@register.simple_tag
def card_chips(obj):
    key = obj.model_key
    chips = []
    if key == "practice.activity":
        chips = [obj.get_kind_display(), obj.get_age_range_display(), obj.get_place_display()]
    elif key == "practice.material":
        chips = [obj.get_kind_display(), obj.get_audience_display()]
        if obj.origin == Origin.COMMUNITY:
            chips.append("Compartido por la comunidad")
    elif key == "practice.video":
        chips = [obj.publisher, obj.language] + (["Con subtítulos"] if obj.has_subtitles else [])
    elif key == "directory.institution":
        chips = [obj.get_kind_display(), f"{obj.canton}, {obj.province}"]
    elif key == "learn.capsule":
        chips = [obj.get_theme_display()]
    elif key == "exchange.exchangeitem":
        chips = [obj.get_offer_display(), obj.get_item_kind_display(), obj.canton, obj.get_availability_display()]
    elif key == "interviews.interview":
        chips = [obj.organization_name]
    return [c for c in chips if c]


@register.filter
def get_item(mapping, key):
    return mapping.get(key, "")


@register.filter
def origin_badge(obj):
    style = {Origin.EDITORIAL: "primary", Origin.INSTITUTIONAL: "info", Origin.COMMUNITY: "warning",
             Origin.PENDING_CHECK: "secondary"}.get(obj.origin, "secondary")
    return format_html('<span class="badge rounded-pill text-bg-{}">{}</span>', style, obj.get_origin_display())


# ---------------------------------------------------------------------------
# Fotografías del sitio (static/img/fotos/). Se asignan por tema o por tipo de
# contenido, así cualquier registro nuevo creado desde la administración
# recibe automáticamente una imagen acorde a su sección.
# ---------------------------------------------------------------------------
FOTOS_TEMA = {
    "que-es": ("cabeza-rompecabezas.jpg", "Silueta de una cabeza con un cerebro formado por piezas de colores."),
    "diversidad": ("nino-bloques-suelo.jpg", "Un niño acostado en el suelo sonríe rodeado de bloques de colores."),
    "comunicacion": ("aula-bloques.jpg", "Un niño juega con cubos en el aula mientras una docente lo anima."),
    "rutinas": ("nino-mesa-bloques.jpg", "Un niño construye una torre de bloques sobre una mesa."),
    "emociones": ("nino-sensorial.jpg", "Un niño se tapa los oídos porque le molesta el ruido."),
    "mitos": ("corazon-rompecabezas.jpg", "Un corazón formado por piezas de rompecabezas de colores."),
    "inclusion": ("nino-parque.jpg", "Un niño sentado en el parque mira a otros niños jugar."),
    "derechos": ("lazo-manos.jpg", "Un lazo de colores junto a cuatro manos de juguete."),
    "ayuda": ("manos-corazon.jpg", "Una mano entrega a otra un corazón hecho de piezas de colores."),
}

FOTOS_MODULO = {
    "learn.capsule": ["cabeza-rompecabezas.jpg"],
    "practice.activity": ["nino-mesa-bloques.jpg", "aula-bloques.jpg", "nino-bloques-suelo.jpg"],
    "practice.material": ["ilustracion-nina.jpg", "ilustracion-rompecabezas.jpg", "corazon-rompecabezas.jpg"],
    "practice.video": ["hablemos-autismo.jpg"],
    "directory.institution": ["manos-corazon.jpg", "lazo-manos.jpg"],
    "interviews.interview": ["hablemos-autismo.jpg"],
    "exchange.exchangeitem": ["ilustracion-rompecabezas.jpg", "corazon-rompecabezas.jpg"],
    "comments.comment": ["corazon-rompecabezas.jpg"],
}


@register.simple_tag
def foto(nombre):
    """Ruta de una fotografía de static/img/fotos/."""
    return static(f"img/fotos/{nombre}")


@register.simple_tag
def foto_tema(theme):
    nombre, _alt = FOTOS_TEMA.get(theme, ("corazon-rompecabezas.jpg", ""))
    return static(f"img/fotos/{nombre}")


@register.simple_tag
def foto_obj(obj):
    """Imagen para la tarjeta de cualquier contenido."""
    key = getattr(obj, "model_key", "")
    if key == "learn.capsule" and getattr(obj, "theme", "") in FOTOS_TEMA:
        return static(f"img/fotos/{FOTOS_TEMA[obj.theme][0]}")
    opciones = FOTOS_MODULO.get(key, ["corazon-rompecabezas.jpg"])
    return static(f"img/fotos/{opciones[(getattr(obj, 'pk', 0) or 0) % len(opciones)]}")

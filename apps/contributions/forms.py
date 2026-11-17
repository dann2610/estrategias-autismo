import re

from django import forms

from apps.comments.models import Comment
from apps.directory.models import Institution
from apps.exchange.models import ExchangeItem
from apps.practice.models import Material

PRIVACY_HELP = ("No incluyas nombres completos, fotografías, direcciones ni datos clínicos de niñas y niños, "
                "ni datos privados de otras personas.")

# Detección básica de datos sensibles antes de enviar (no sustituye la moderación humana)
SENSITIVE_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "parece incluir un número de cédula o de teléfono personal"),
    (re.compile(r"\b(calle|avenida|av\.|mz\.|manzana|villa|solar)\s", re.I), "parece incluir una dirección"),
    (re.compile(r"\b(diagn[oó]stico|medicaci[oó]n|medicamento|mg)\b", re.I), "parece incluir datos clínicos"),
]


def scan_sensitive(form, field_names):
    for name in field_names:
        value = form.cleaned_data.get(name) or ""
        for pattern, msg in SENSITIVE_PATTERNS:
            if pattern.search(value):
                form.add_error(name, f"Por privacidad, revisa este texto: {msg}.")
                break


class HoneypotMixin(forms.Form):
    """Campo oculto que las personas no ven ni completan; los robots de spam sí."""
    website = forms.CharField(required=False, label="No completes este campo",
                              widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("No se pudo enviar el formulario.")
        return ""


class ContributionForm(HoneypotMixin, forms.ModelForm):
    accept_rules = forms.BooleanField(
        label="Acepto las normas de convivencia y la política de privacidad, y entiendo que mi aporte "
              "será revisado antes de publicarse.")
    scan_fields = ("title", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "description" in self.fields:
            self.fields["description"].help_text = PRIVACY_HELP
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 4)
        if self.instance and self.instance.pk:
            self.fields["accept_rules"].initial = True

    def clean(self):
        cleaned = super().clean()
        scan_sensitive(self, self.scan_fields)
        return cleaned


class MaterialShareForm(ContributionForm):
    class Meta:
        model = Material
        fields = ("title", "kind", "description", "how_to_use", "file", "external_url", "age_range", "audience",
                  "credit", "license", "rights_confirmed")
        labels = {"credit": "Autoría", "rights_confirmed": "Soy autor/a del material o tengo permiso para compartirlo"}
        help_texts = {"license": "Ej.: «Uso libre con atribución» o la licencia del material original."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rights_confirmed"].required = True
        self.fields["credit"].required = True
        self.fields["kind"].choices = [c for c in self.fields["kind"].choices
                                       if c[0] in ("", "agenda", "secuencia", "tarjetas", "tablero", "ficha", "juego",
                                                   "documento")]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("file") and not cleaned.get("external_url") and not (self.instance and self.instance.file):
            self.add_error("file", "Sube un archivo PDF, PNG o JPG, o indica un enlace legítimo.")
        return cleaned


class ExchangeForm(ContributionForm):
    class Meta:
        model = ExchangeItem
        fields = ("title", "offer", "item_kind", "condition", "description", "province", "canton",
                  "contact_authorized", "delivery_terms", "safety_confirmed")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("offer") == ExchangeItem.Offer.OFFER and not cleaned.get("safety_confirmed"):
            self.add_error("safety_confirmed", "Confirma que el material es seguro y está limpio.")
        return cleaned


class InstitutionSuggestForm(ContributionForm):
    class Meta:
        model = Institution
        fields = ("title", "kind", "description", "services", "province", "canton", "website", "social", "phone",
                  "email", "evidence_url")
        labels = {"title": "Nombre de la institución",
                  "description": "¿Qué sabes de esta institución y por qué la sugieres?",
                  "evidence_url": "¿Dónde viste esta información? (enlace)"}
        help_texts = {"phone": "Solo datos públicos de la institución.",
                      "evidence_url": "Sitio oficial, red social oficial o noticia. El equipo verificará antes de publicar."}


class CommentForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("description",)
        labels = {"description": "Tu comentario o pregunta"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3, "maxlength": 1500})}

    def clean(self):
        cleaned = super().clean()
        scan_sensitive(self, ("description",))
        return cleaned

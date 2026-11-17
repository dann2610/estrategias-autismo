"""Tipos de aporte disponibles en «Participar» y registro de modelos con moderación."""
from dataclasses import dataclass
from itertools import chain

from django.apps import apps

from . import forms as f


@dataclass(frozen=True)
class ContributionType:
    slug: str
    label: str
    pictogram: str
    help: str
    model_key: str
    form_class: type

    @property
    def model(self):
        return apps.get_model(self.model_key)


TYPES = [
    ContributionType("material", "Compartir un material educativo", "1f4dd",
                     "Una agenda, ficha o plantilla que hayas creado y quieras compartir (PDF, PNG o JPG).",
                     "practice.material", f.MaterialShareForm),
    ContributionType("intercambio", "Publicar en el intercambio de materiales", "1f4e6",
                     "Ofrece o busca libros, juegos o materiales de apoyo para intercambiar o prestar.",
                     "exchange.exchangeitem", f.ExchangeForm),
    ContributionType("institucion", "Sugerir una institución o servicio", "1f3eb",
                     "Cuéntanos de una institución que conozcas. El equipo verificará los datos antes de publicarla.",
                     "directory.institution", f.InstitutionSuggestForm),
]
TYPES_BY_SLUG = {t.slug: t for t in TYPES}

MODERATED_MODEL_KEYS = [
    "learn.capsule", "practice.activity", "practice.material", "practice.video", "directory.institution",
    "interviews.interview", "exchange.exchangeitem", "comments.comment",
]


def moderated_models():
    return [apps.get_model(k) for k in MODERATED_MODEL_KEYS]


def get_moderated_model(model_key):
    if model_key not in MODERATED_MODEL_KEYS:
        return None
    return apps.get_model(model_key)


def type_for_object(obj):
    for t in TYPES:
        if t.model_key == obj.model_key:
            return t
    return None


def user_contributions(user, status=None):
    querysets = []
    for key in ("practice.material", "exchange.exchangeitem", "directory.institution", "comments.comment"):
        qs = apps.get_model(key).objects.filter(author=user)
        if status:
            qs = qs.filter(status=status)
        querysets.append(qs)
    return sorted(chain(*querysets), key=lambda o: o.updated_at, reverse=True)

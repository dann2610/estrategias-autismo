import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.contributions.registry import get_moderated_model
from apps.directory.models import Institution
from apps.exchange.models import ExchangeItem
from apps.interviews.models import Interview
from apps.learn.models import FAQ, Capsule
from apps.practice.models import Activity, Material, Video

from .models import Favorite, Source, Topic
from .permissions import is_moderator


def home(request):
    return render(request, "core/home.html", {
        "capsules": Capsule.objects.public().order_by("order")[:3],
        "activities": Activity.objects.public().order_by("-featured", "title")[:3],
        "materials": Material.objects.public().order_by("-featured", "title")[:4],
        "topics": Topic.objects.all(),
        "institutions_count": Institution.objects.public().count(),
        "interviews": Interview.objects.public()[:2],
        "upcoming_interview": Interview.objects.exclude(status="aprobado").filter(show_as_upcoming=True).first(),
        "exchange_count": ExchangeItem.objects.public().exclude(availability="finalizado").count(),
    })


def orientation(request):
    """Área 3: recursos, orientación y comunidad."""
    return render(request, "core/orientation.html", {
        "institutions_count": Institution.objects.public().count(),
        "interviews": Interview.objects.public()[:2],
        "upcoming": Interview.objects.exclude(status="aprobado").filter(show_as_upcoming=True).exists(),
        "videos": Video.objects.public()[:3],
        "shared_materials": Material.objects.public().filter(origin="comunidad")[:3],
        "exchange_count": ExchangeItem.objects.public().exclude(availability="finalizado").count(),
        "faqs": FAQ.objects.filter(published=True)[:4],
    })


SEARCH_TARGETS = [
    (Capsule, "Aprende sobre el autismo", ("title", "description", "explanation")),
    (Activity, "Actividades", ("title", "description", "objective")),
    (Material, "Materiales y apoyos visuales", ("title", "description")),
    (Video, "Recursos audiovisuales", ("title", "description", "publisher")),
    (Institution, "Directorio", ("title", "description", "canton", "services")),
    (Interview, "Entrevistas", ("title", "description", "organization_name")),
]


def search(request):
    q = (request.GET.get("q") or "").strip()[:100]
    groups = []
    if len(q) >= 2:
        for model, label, fields in SEARCH_TARGETS:
            cond = Q()
            for f in fields:
                cond |= Q(**{f"{f}__icontains": q})
            items = list(model.objects.public().filter(cond)[:6])
            if items:
                groups.append((label, items))
    return render(request, "core/search.html", {"q": q, "groups": groups})


def topic(request, slug):
    """Página de un tema: reúne todo lo publicado que comparte la misma etiqueta."""
    t = get_object_or_404(Topic, slug=slug)
    return render(request, "core/topic.html", {
        "topic": t,
        "capsules": t.capsules.public(),
        "activities": t.activities.public(),
        "materials": t.materials.public(),
        "videos": t.videos.public(),
        "interviews": t.interviews.public(),
        "institutions": t.institutions.public(),
        "sources": t.sources.all(),
    })


def sources(request):
    kind = request.GET.get("tipo")
    qs = Source.objects.all()
    if kind in Source.Kind.values:
        qs = qs.filter(kind=kind)
    return render(request, "core/sources.html", {"sources": qs, "kinds": Source.Kind.choices, "current": kind})


@login_required
@require_POST
def toggle_favorite(request, model_key, pk):
    model = get_moderated_model(model_key)
    if not model:
        raise Http404
    obj = model.objects.public().filter(pk=pk).first()
    if not obj:
        raise Http404
    ct = ContentType.objects.get_for_model(model)
    fav, created = Favorite.objects.get_or_create(user=request.user, content_type=ct, object_id=obj.pk)
    if not created:
        fav.delete()
        messages.info(request, "Quitado de tus favoritos.")
    else:
        messages.success(request, "Guardado en tus favoritos.")
    nxt = request.POST.get("next") or obj.get_absolute_url()
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = obj.get_absolute_url()
    return redirect(nxt)


def serve_file(request, model_key, pk, field):
    """Sirve archivos subidos con control de acceso: los públicos solo si el contenido está aprobado;
    los privados (respaldos, autorizaciones) solo para su autor y el equipo de moderación."""
    model = get_moderated_model(model_key)
    if not model or field not in (model.PUBLIC_FILE_FIELDS + model.PRIVATE_FILE_FIELDS):
        raise Http404
    obj = model.objects.filter(pk=pk).first()
    if not obj:
        raise Http404
    owner = request.user.is_authenticated and obj.author_id == request.user.pk
    allowed = is_moderator(request.user) or owner
    if field in model.PUBLIC_FILE_FIELDS and obj.is_public:
        allowed = True
    f = getattr(obj, field)
    if not allowed or not f:
        raise Http404
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    response = FileResponse(f.open("rb"), content_type=ctype)
    ext = f.name[f.name.rfind("."):]
    response["Content-Disposition"] = f'inline; filename="{model._meta.model_name}-{pk}{ext}"'
    response["Cache-Control"] = "private, max-age=0" if field in model.PRIVATE_FILE_FIELDS else "public, max-age=3600"
    return response


def static_page(template):
    def view(request):
        return render(request, template)
    return view


def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def error_403(request, exception):
    return render(request, "403.html", status=403)

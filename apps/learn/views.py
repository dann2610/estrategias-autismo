from django.shortcuts import render

from apps.comments.models import Comment
from apps.contributions.forms import CommentForm
from apps.core.choices import Status
from apps.core.listing import detail
from apps.core.models import SiteConfig

from .models import FAQ, Capsule


def index(request):
    """Área 1: Comprender el autismo."""
    return render(request, "learn/index.html", {"capsules": Capsule.objects.public().order_by("order")})


def capsule(request, pk):
    def extra(obj):
        topics = obj.topics.all()
        acts = list(obj.related_activities.public())
        mats = list(obj.related_materials.public())
        vids = list(obj.related_videos.public())
        # Recursos adicionales que comparten temas, para seguir explorando
        more_acts = (obj.related_activities.model.objects.public().filter(topics__in=topics)
                     .exclude(pk__in=[a.pk for a in acts]).distinct()[:3])
        own_pending = Comment.objects.none()
        if request.user.is_authenticated:
            own_pending = obj.comments.filter(author=request.user).exclude(status=Status.APPROVED)
        ordered = list(Capsule.objects.public().order_by("order", "title"))
        idx = next((i for i, c in enumerate(ordered) if c.pk == obj.pk), None)
        return {
            "activities": acts, "materials": mats, "videos": vids, "more_activities": more_acts,
            "comments": obj.comments.public(), "own_pending": own_pending, "comment_form": CommentForm(),
            "comments_enabled": SiteConfig.load().allow_comments,
            "prev": ordered[idx - 1] if idx else None,
            "next": ordered[idx + 1] if idx is not None and idx + 1 < len(ordered) else None,
        }
    return detail(request, Capsule, pk, "learn/capsule.html", extra=extra)


def faq(request):
    return render(request, "learn/faq.html", {"faqs": FAQ.objects.filter(published=True)})

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification


@login_required
def inbox(request):
    page = Paginator(request.user.notifications.all(), 20).get_page(request.GET.get("page"))
    return render(request, "notifications/inbox.html", {"page_obj": page})


@login_required
@require_POST
def open_notification(request, pk):
    # Solo se pueden abrir notificaciones propias
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.read = True
    n.save(update_fields=["read"])
    if n.url and url_has_allowed_host_and_scheme(n.url, allowed_hosts={request.get_host()}):
        return redirect(n.url)
    return redirect("notifications:inbox")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(read=False).update(read=True)
    return redirect("notifications:inbox")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    return Response({"no_leidas": request.user.notifications.filter(read=False).count()})

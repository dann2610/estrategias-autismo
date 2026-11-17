from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import redirect, render

from apps.core.ratelimit import ratelimit
from apps.notifications.services import notify_moderators

from .models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reference", "reason", "details")
        widgets = {"details": forms.Textarea(attrs={"rows": 4})}


@login_required
@ratelimit("report", limit=10, period=3600)
def create_report(request, model_key=None, pk=None):
    item = None
    if model_key:
        try:
            app_label, model = model_key.split(".")
            ct = ContentType.objects.get(app_label=app_label, model=model)
            item = ct.get_object_for_this_type(pk=pk)
        except Exception:
            raise Http404
        if not getattr(item, "is_public", False):
            raise Http404
    form = ReportForm(request.POST or None)
    if item:
        form.fields.pop("reference")
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.reporter = request.user
        if item:
            report.content_type = ContentType.objects.get_for_model(item)
            report.object_id = item.pk
        report.save()
        notify_moderators("Nuevo reporte de la comunidad pendiente de revisión.", "/panel/reportes/")
        messages.success(request, "Gracias. Tu reporte fue enviado al equipo de moderación.")
        return redirect(item.get_absolute_url() if item else "accounts:panel")
    return render(request, "reports/form.html", {"form": form, "item": item})

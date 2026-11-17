from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator

from apps.contributions.registry import user_contributions
from apps.core.models import Favorite
from apps.core.ratelimit import ratelimit

from .forms import EmailLoginForm, ProfileForm, SignupForm, UserNameForm
from .models import Profile


@ratelimit("signup", limit=5, period=600)
def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:panel")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "¡Bienvenida/o! Tu cuenta se creó correctamente.")
        return redirect("accounts:panel")
    return render(request, "accounts/signup.html", {"form": form})


@method_decorator(ratelimit("login", limit=8, period=300), name="dispatch")
class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


@login_required
def panel(request):
    items = user_contributions(request.user)
    counts = {}
    for it in items:
        counts[it.get_status_display()] = counts.get(it.get_status_display(), 0) + 1
    return render(request, "accounts/panel.html", {
        "recent": items[:5],
        "counts": counts,
        "favorites_count": Favorite.objects.filter(user=request.user).count(),
        "notifications": request.user.notifications.all()[:5],
    })


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    uform = UserNameForm(request.POST or None, instance=request.user)
    pform = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and uform.is_valid() and pform.is_valid():
        uform.save()
        pform.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("accounts:panel")
    return render(request, "accounts/profile_form.html", {"uform": uform, "pform": pform})


@login_required
def favorites(request):
    favs = [f for f in Favorite.objects.filter(user=request.user).select_related("content_type")
            if f.item is not None and getattr(f.item, "is_public", False)]
    return render(request, "accounts/favorites.html", {"favorites": favs})

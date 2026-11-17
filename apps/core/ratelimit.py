"""Limitación sencilla de solicitudes basada en la caché, para formularios sensibles."""
import functools
import time

from django.core.cache import cache
from django.shortcuts import render


def client_ip(request):
    # Detrás de un proxy de confianza, configure el servidor para que REMOTE_ADDR sea la IP real.
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def ratelimit(scope, limit, period=60, methods=("POST",)):
    """Permite `limit` solicitudes cada `period` segundos por usuario (o IP si no hay sesión)."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method in methods:
                ident = f"u{request.user.pk}" if request.user.is_authenticated else f"ip{client_ip(request)}"
                window = int(time.time() // period)
                key = f"rl:{scope}:{ident}:{window}"
                count = cache.get_or_set(key, 0, period)
                if count >= limit:
                    return render(request, "429.html", status=429)
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, period)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

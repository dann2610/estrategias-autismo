from django.conf import settings

from .models import SiteConfig
from .permissions import can_manage_users, can_view_stats, is_moderator


def site(request):
    user = request.user
    unread = 0
    if user.is_authenticated:
        unread = user.notifications.filter(read=False).count()
    try:
        config = SiteConfig.load()
    except Exception:  # base de datos aún sin migrar
        config = None
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "site_config": config,
        "unread_notifications": unread,
        "user_is_moderator": is_moderator(user),
        "user_can_manage_users": can_manage_users(user),
        "user_can_view_stats": can_view_stats(user),
    }

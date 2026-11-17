from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Notification


def notify(user, message, url=""):
    if user and user.is_active:
        return Notification.objects.create(user=user, message=message[:500], url=url)


def moderators():
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(
        Q(is_superuser=True)
        | Q(user_permissions__codename="moderate_content")
        | Q(groups__permissions__codename="moderate_content")
    ).distinct()


def notify_moderators(message, url=""):
    Notification.objects.bulk_create([Notification(user=u, message=message[:500], url=url)
                                      for u in moderators()])

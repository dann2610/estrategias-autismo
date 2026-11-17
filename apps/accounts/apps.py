from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Cuentas"

    def ready(self):
        from django.db.models.signals import post_save

        from .models import Profile, User

        def ensure_profile(sender, instance, created, **kwargs):
            if created:
                Profile.objects.get_or_create(user=instance)

        post_save.connect(ensure_profile, sender=User, dispatch_uid="ensure_profile")

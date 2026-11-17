from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ADMIN_APPS = ["learn", "practice", "directory", "interviews", "exchange", "comments", "reports", "core",
              "notifications"]


class Command(BaseCommand):
    help = "Crea o actualiza los grupos Administradores y Moderadores con sus permisos."

    def handle(self, *args, **options):
        mod_perm = Permission.objects.get(codename="moderate_content")
        users_perm = Permission.objects.get(codename="manage_users")
        stats_perm = Permission.objects.get(codename="view_statistics")

        admins, _ = Group.objects.get_or_create(name="Administradores")
        content_perms = Permission.objects.filter(content_type__app_label__in=ADMIN_APPS)
        audit_view = Permission.objects.filter(content_type__app_label="moderation", codename__startswith="view_")
        user_perms = Permission.objects.filter(content_type__app_label="accounts",
                                               codename__in=["view_user", "change_user", "view_profile",
                                                             "change_profile"])
        admins.permissions.set(list(content_perms) + list(audit_view) + list(user_perms)
                               + [mod_perm, users_perm, stats_perm])

        # Rol preparado para el futuro: solo revisa contenido, sin gestionar cuentas ni configuración
        moderators, _ = Group.objects.get_or_create(name="Moderadores")
        view_perms = Permission.objects.filter(content_type__app_label__in=ADMIN_APPS, codename__startswith="view_")
        moderators.permissions.set(list(view_perms) + [mod_perm])

        self.stdout.write(self.style.SUCCESS("Roles configurados: Administradores y Moderadores."))

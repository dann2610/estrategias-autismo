"""
Creación segura del primer administrador.

Uso interactivo:  python manage.py crear_admin
Uso automatizado: ADMIN_EMAIL=... ADMIN_PASSWORD=... python manage.py crear_admin --no-input

La contraseña nunca se escribe en el repositorio ni se muestra en pantalla.
"""
import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea el primer administrador de la plataforma de forma segura."

    def add_arguments(self, parser):
        parser.add_argument("--no-input", action="store_true", help="Leer ADMIN_EMAIL y ADMIN_PASSWORD del entorno.")
        parser.add_argument("--permitir-otro", action="store_true",
                            help="Permite crear un administrador adicional si ya existe uno.")

    def handle(self, *args, **opts):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists() and not opts["permitir_otro"]:
            raise CommandError("Ya existe un administrador. Use --permitir-otro si realmente necesita otro.")
        if opts["no_input"]:
            email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
            password = os.environ.get("ADMIN_PASSWORD", "")
        else:
            email = input("Correo del administrador: ").strip().lower()
            password = getpass.getpass("Contraseña: ")
            if password != getpass.getpass("Repite la contraseña: "):
                raise CommandError("Las contraseñas no coinciden.")
        if not email or not password:
            raise CommandError("Se requieren correo y contraseña.")
        if User.objects.filter(email=email).exists():
            raise CommandError("Ya existe una cuenta con ese correo.")
        user = User(email=email, first_name="Administración")
        try:
            validate_password(password, user)
        except ValidationError as e:
            raise CommandError(" ".join(e.messages))
        user = User.objects.create_superuser(email=email, password=password, first_name="Administración")
        call_command("configurar_roles")
        user.groups.add(Group.objects.get(name="Administradores"))
        self.stdout.write(self.style.SUCCESS(f"Administrador creado: {email}"))

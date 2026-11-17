from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.core.choices import PROVINCE_CHOICES


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)  # se guarda con hash; nunca en texto plano
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Usuario que inicia sesión con su correo electrónico."""
    username = None
    email = models.EmailField("correo electrónico", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.email

    @property
    def public_name(self):
        profile = getattr(self, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return self.first_name or "Miembro de la comunidad"


class Profile(models.Model):
    class Participation(models.TextChoices):
        FAMILY = "familia", "Familia / cuidador"
        TEACHER = "docente", "Docente"
        PROFESSIONAL = "profesional", "Profesional"
        OTHER = "otro", "Otro miembro de la comunidad"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField("nombre público", max_length=60, blank=True,
                                    help_text="Cómo te verán otras personas. Puede ser un seudónimo.")
    participation = models.CharField("tipo de participación", max_length=20,
                                     choices=Participation.choices, default=Participation.FAMILY)
    province = models.CharField("provincia", max_length=40, choices=PROVINCE_CHOICES, default="Guayas")
    canton = models.CharField("cantón", max_length=60, blank=True)
    bio = models.TextField("sobre mí (opcional)", max_length=500, blank=True)
    accepted_terms_at = models.DateTimeField("aceptó normas y privacidad", null=True, blank=True)
    suspension_reason = models.TextField("motivo de suspensión", blank=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"Perfil de {self.user}"

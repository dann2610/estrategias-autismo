from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile, User


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=60)
    display_name = forms.CharField(label="Nombre público (opcional)", max_length=60, required=False,
                                   help_text="Puedes usar un seudónimo para proteger tu privacidad.")
    participation = forms.ChoiceField(label="¿Cómo participas?", choices=Profile.Participation.choices)
    accept = forms.BooleanField(label="Acepto las normas de la comunidad y la política de privacidad")

    class Meta:
        model = User
        fields = ("email", "first_name")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def save(self, commit=True):
        from django.utils import timezone
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # Un registro público jamás crea cuentas con privilegios
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            Profile.objects.update_or_create(user=user, defaults={
                "display_name": self.cleaned_data.get("display_name", ""),
                "participation": self.cleaned_data["participation"],
                "accepted_terms_at": timezone.now(),
            })
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico",
                                widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))


class UserNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")


class ProfileForm(forms.ModelForm):
    """El usuario solo puede editar datos de su perfil. Rol, permisos y estado de la
    cuenta no forman parte del formulario, por lo que no pueden manipularse."""

    class Meta:
        model = Profile
        fields = ("display_name", "participation", "province", "canton", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

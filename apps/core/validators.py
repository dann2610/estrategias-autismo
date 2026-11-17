"""Validación segura de archivos subidos: tamaño, extensión y contenido real."""
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}


def validate_upload(file):
    max_bytes = settings.UPLOAD_MAX_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"El archivo supera el tamaño máximo de {settings.UPLOAD_MAX_MB} MB.")
    ext = Path(file.name).suffix.lower()
    if ext not in ALLOWED:
        raise ValidationError("Formato no permitido. Solo se aceptan PDF, PNG o JPG.")
    pos = file.tell() if hasattr(file, "tell") else 0
    file.seek(0)
    head = file.read(16)
    file.seek(pos)
    if not any(head.startswith(sig) for sig in ALLOWED[ext]):
        raise ValidationError("El contenido del archivo no coincide con su extensión.")


def upload_path(instance, filename):
    """Guarda con un nombre aleatorio para no exponer nombres originales."""
    import uuid
    ext = Path(filename).suffix.lower()
    return f"{instance._meta.app_label}/{instance._meta.model_name}/{uuid.uuid4().hex}{ext}"

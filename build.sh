#!/usr/bin/env bash
# Script de construcción para Render (se ejecuta en cada despliegue).
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Carga el contenido inicial SOLO la primera vez (si la base está vacía),
# para no sobrescribir lo que el administrador edite después.
if python manage.py shell -c "import sys; from apps.learn.models import Capsule; sys.exit(0 if Capsule.objects.exists() else 1)"; then
  echo "Contenido ya cargado: se omite cargar_contenido."
else
  python manage.py cargar_contenido
fi

# Crea el primer administrador si se definieron ADMIN_EMAIL y ADMIN_PASSWORD
# (si ya existe, no hace nada).
if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
  python manage.py crear_admin --no-input || echo "El administrador ya existe o no se pudo crear (ver mensaje arriba)."
fi

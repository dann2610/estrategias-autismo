# Despliegue en un servidor

> ¿Vas a usar **Render**? Sigue la guía `docs/render.md`, que es más sencilla.

Ejemplo para un servidor Linux con PostgreSQL, Gunicorn y Nginx.

1. Crea la base de datos y su usuario en PostgreSQL.
2. Copia el proyecto, crea el entorno virtual e instala las dependencias: `pip install -r requirements.txt`.
3. Crea el archivo `.env` con estos valores:

```
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clave larga generada>
DJANGO_ALLOWED_HOSTS=midominio.ec
DJANGO_CSRF_TRUSTED_ORIGINS=https://midominio.ec
DATABASE_URL=postgres://usuario:clave@localhost:5432/comprender_autismo
DJANGO_MEDIA_ROOT=/srv/comprender_autismo_media
SITE_CONTACT_EMAIL=correo-real@...
```

Configura también el correo SMTP para la recuperación de contraseñas.

4. Ejecuta:

```
python manage.py migrate
python manage.py collectstatic
python manage.py cargar_contenido
python manage.py crear_admin
python manage.py check --deploy
```

5. Inicia Gunicorn: `gunicorn config.wsgi --bind 127.0.0.1:8001 --workers 3`.
6. Configura Nginx con HTTPS (Let's Encrypt):
   - sirve `/static/` desde `staticfiles/`;
   - envía el resto a Gunicorn;
   - **no publiques la carpeta `media`**: los archivos se entregan a través de Django, que controla los permisos.
7. Si usas varios procesos, define `REDIS_URL` para que el límite de solicitudes se comparta entre ellos.

Copias de seguridad: haz un `pg_dump` diario de la base de datos y una copia de la carpeta `media`.

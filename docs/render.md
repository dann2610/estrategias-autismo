# Publicar el sitio en Render

El proyecto ya trae todo lo necesario:

- `render.yaml`: crea en Render la base de datos PostgreSQL y el servicio web.
- `build.sh`: instala las dependencias, prepara los archivos estáticos y crea las tablas. Solo la primera vez, también carga el contenido y crea el administrador.
- WhiteNoise sirve el CSS, el JS y las imágenes, así que no hace falta Nginx.

## 1. Subir el proyecto a GitHub

1. Crea una cuenta en <https://github.com> y un repositorio nuevo, por ejemplo `estrategias-autismo`. Puede ser privado.
2. Desde la carpeta que contiene `manage.py`, en la terminal de VS Code:

```powershell
git init
git add .
git commit -m "Primera versión"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/estrategias-autismo.git
git push -u origin main
```

> **No subas el archivo `.env`.** El `.gitignore` ya lo excluye cuando usas Git. Si subes los archivos arrastrándolos en la página de GitHub, **no arrastres `.env`, `db.sqlite3`, `.venv` ni `staticfiles`**.

## 2. Crear el sitio en Render

1. Entra a <https://render.com> y regístrate **con tu cuenta de GitHub**.
2. Pulsa **New +** y luego **Blueprint**.
3. Elige tu repositorio. Render lee `render.yaml` y te muestra la base de datos `estrategias-autismo-db` y el servicio web `estrategias-autismo`.
4. Te pedirá dos valores:
   - `ADMIN_EMAIL`: el correo con el que entrarás como administrador.
   - `ADMIN_PASSWORD`: una contraseña de **al menos 10 caracteres**, que no sea solo números ni una contraseña común.
5. Pulsa **Apply** o **Deploy Blueprint** y espera entre 5 y 10 minutos. Puedes ver el avance en **Logs**.
6. Al terminar, verás el enlace del sitio, por ejemplo `https://estrategias-autismo.onrender.com`.
7. El panel de administración está en `https://...onrender.com/panel/` y `https://...onrender.com/gestion-django/`.

## 3. Actualizar el sitio

Cada vez que hagas cambios:

```powershell
git add .
git commit -m "Describe el cambio"
git push
```

Render vuelve a desplegar el sitio solo. El contenido que edites desde la administración **no se borra**, porque `cargar_contenido` solo se ejecuta cuando la base de datos está vacía.

## Limitaciones del plan gratuito

- **El sitio se «duerme»** después de unos 15 minutos sin visitas. La siguiente visita tarda entre 30 y 60 segundos en cargar. Abre el sitio un minuto antes de presentarlo.
- **La base de datos gratuita vence** al cabo de un tiempo (Render avisa por correo). Para la defensa no es problema, pero si el sitio debe seguir en línea, habrá que pasar a un plan pagado o volver a crearla.
- **Los archivos que suben los usuarios** (documentos de respaldo y materiales en PDF) se guardan en el disco del servidor, y en el plan gratuito ese disco **se borra en cada despliegue o reinicio**. Los textos y los registros están en PostgreSQL y no se pierden. Si se necesitan archivos permanentes, hay que agregar un disco persistente (plan pagado) y definir `DJANGO_MEDIA_ROOT` con su ruta.
- El correo de recuperación de contraseña se imprime en los Logs, hasta que se configure el SMTP con `DJANGO_EMAIL_BACKEND`, `EMAIL_HOST`, etc.

## Si algo falla

| Mensaje en los Logs | Solución |
|---|---|
| `Falta la variable de entorno DJANGO_SECRET_KEY` | En el servicio web, ve a **Environment** y verifica que exista `DJANGO_SECRET_KEY`. |
| `Bad Request (400)` al abrir el sitio | Agrega tu dominio en `DJANGO_ALLOWED_HOSTS`. El dominio `.onrender.com` ya se agrega solo. |
| `CSRF verification failed` al iniciar sesión | Agrega `https://tu-dominio` en `DJANGO_CSRF_TRUSTED_ORIGINS`. |
| `Ya existe un administrador` | Es normal en los despliegues que siguen al primero. |
| `La contraseña es demasiado corta` / `común` | Cambia `ADMIN_PASSWORD` en **Environment** y pulsa **Manual Deploy**. |
| El sitio se ve sin estilos | Revisa que en los Logs aparezca `collectstatic` sin errores. |

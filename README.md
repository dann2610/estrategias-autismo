# Estrategias de apoyo en el autismo

*Comprender y acompañar con amor.*

Un espacio de orientación, recursos y aprendizaje para familias y docentes.

Plataforma web del proyecto de Titulación de la carrera de Comunicación (UNEMI). Está dirigida a familias, cuidadores y docentes de niñas y niños de 3 a 12 años con autismo, en Milagro y la provincia del Guayas.

El contenido es educativo y orientativo. No reemplaza el diagnóstico ni el tratamiento profesional.

## Las tres áreas

| Área | Qué contiene |
|---|---|
| **Aprende sobre el autismo** (`/comprender/`) | 9 cápsulas educativas con una estructura de 10 partes y un gráfico explicativo con texto alternativo. Cada cápsula enlaza a actividades y materiales concretos y muestra sus fuentes verificables. También hay preguntas frecuentes. |
| **Actividades y recursos** (`/actividades-y-recursos/`) | 9 actividades: objetivo, materiales, pasos, edad, adaptaciones y precauciones. 10 materiales imprimibles. Banco de 54 pictogramas. Creador de agendas visuales. Videos recomendados. |
| **Orientación y comunidad** (`/orientacion/`) | Directorio de instituciones con la fuente y la base de su verificación. Entrevistas (por ahora «Contenido próximamente»). Intercambio de materiales educativos y de apoyo, siempre moderado. |

Hay tres roles: **visitante** (lee, imprime y crea agendas), **usuario registrado** (comenta, guarda favoritos, comparte materiales y publica en el intercambio; todo pasa por revisión) y **administrador/moderador** (usa el panel `/panel/` y la gestión de contenidos `/gestion-django/`).

## Tecnología

Python 3.12 o superior, Django 5.2, SQLite (incluida, no se instala nada) y Bootstrap 5. Las fuentes, los íconos y Bootstrap están incluidos en el proyecto, así que el sitio funciona sin depender de servicios externos.

## Instalación en Windows (paso a paso)

> **Importante:** al descomprimir el ZIP, Windows a veces crea una carpeta dentro de otra: `comprender_autismo\comprender_autismo\`. Entra a la carpeta **que contiene `manage.py`** y trabaja siempre desde ahí.

1. Instala **Python** (marca «Add Python to PATH»). No necesitas instalar ni crear ninguna base de datos: el proyecto usa SQLite y el archivo `db.sqlite3` se crea solo.
2. Abre la carpeta en VS Code y, en la terminal (PowerShell), ejecuta:

```powershell
cd comprender_autismo            # solo si ves otra carpeta con el mismo nombre
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # si da error: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

3. El archivo `.env` ya viene listo (modo desarrollo). No hay que editar nada.

4. Crea las tablas, carga el contenido y crea tu administrador:

```powershell
python manage.py migrate
python manage.py cargar_contenido
python manage.py crear_admin
python manage.py runserver
```

5. Abre <http://127.0.0.1:8000>. Para administrar, ingresa con tu cuenta y entra a <http://127.0.0.1:8000/panel/>.

Si quieres cuentas de prueba, ejecuta `python manage.py cargar_contenido --usuarios-demo` (solo funciona en modo desarrollo). Se crean dos cuentas:

- `familia.demo@ejemplo.org` / `Demo-familia-2026`
- `docente.demo@ejemplo.org` / `Demo-docente-2026`

## Pruebas

```powershell
python manage.py test
```

Son 22 pruebas. Revisan, entre otras cosas:

- que las cápsulas estén conectadas con recursos prácticos y fuentes;
- que el flujo de moderación funcione y que solo el autor pueda cambiar la disponibilidad en el intercambio;
- que el contacto quede oculto para los visitantes;
- la protección contra spam (honeypot) y la detección de datos sensibles;
- la protección de los archivos privados;
- que no haya enlaces internos rotos para los tres roles.

## Documentación

- `docs/modelo_de_datos.md`: tablas y relaciones.
- `docs/guia_administracion.md`: cómo publicar, moderar y verificar.
- `docs/render.md`: cómo publicar el sitio gratis en Render (paso a paso).
- `docs/despliegue.md`: cómo publicar el sitio en un servidor propio.
- `docs/contenido_pendiente.md`: lo que falta verificar o completar antes de la presentación.

## Créditos

- Pictogramas: Twemoji, © Twitter, Inc. y otros colaboradores, licencia CC BY 4.0.
- Ilustraciones del carrusel y de los encabezados: originales del proyecto (`static/img/ilustraciones/`).
- Tipografía: Lexend (SIL Open Font License).
- Bootstrap y Bootstrap Icons: licencia MIT.

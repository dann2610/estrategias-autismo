# Guía de administración

## Roles

- **Administradores**: todo el sitio, incluidas las cuentas, las estadísticas y la configuración. Se crean con `python manage.py crear_admin`.
- **Moderadores**: revisan aportes, comentarios y reportes. Para crear uno, en `/gestion-django/` → Usuarios, marca «Es staff» y agrega la cuenta al grupo «Moderadores».
- **Usuarios registrados**: lo que publican queda en revisión hasta que alguien del equipo lo apruebe.

## Panel `/panel/`

- **Publicaciones pendientes**: abre cada aporte, revisa la lista de control y elige aprobar, solicitar cambios (con motivo) o rechazar (con motivo). El autor recibe una notificación.
- **Si el sistema no deja publicar**, aparece un recuadro «Todavía no se puede publicar» con lo que falta. Por ejemplo, una institución sin base de verificación o una entrevista sin autorización.
- **Reportes**: se revisan y se marcan como resueltos.
- **Calidad del contenido**: lista lo que necesita atención, como cápsulas sin revisión profesional o instituciones con más de un año sin revisar.
- **Historial y auditoría**: muestran quién hizo cada cambio.

## Publicar una cápsula nueva

1. Entra a `/gestion-django/` → Cápsulas → Agregar y completa las 10 partes, en el orden de los bloques.
2. Elige un gráfico existente o sube una imagen. Si subes una imagen, escribe su texto alternativo.
3. Vincula al menos una actividad o un material, y al menos una fuente. Si la fuente no existe, créala antes en «Fuentes», con la cita APA y la fecha de consulta.
4. Cuando un profesional la revise, completa el campo «Revisión profesional» con su nombre y profesión.

## Directorio: cómo verificar una institución

Elige la base que corresponde. No son lo mismo:

- **Acreditación**: una autoridad evaluó la calidad del servicio.
- **Autorización**: una autoridad permitió su funcionamiento (por ejemplo, un permiso de la ACESS o del Ministerio de Educación).
- **Registro**: consta en un registro oficial (RUC, registro de organizaciones sociales).
- **Información pública**: datos publicados por la propia institución o por un medio o entidad oficial.
- **Autodescripción**: datos enviados por la institución sin otra comprobación.

Siempre guarda el enlace de respaldo y la fecha de revisión. Puedes subir un documento privado como respaldo.

## Entrevistas

La entrevista está creada como **borrador**, con la guía de 10 preguntas. Por eso el sitio muestra «Contenido próximamente».

Para publicarla:

1. Completa la organización, la persona, el cargo y la fecha.
2. Escribe las respuestas reales.
3. Agrega el video (ID de YouTube) o la transcripción.
4. Marca «Autorización confirmada» y sube el documento firmado.
5. Envíala a revisión y apruébala.

No publiques respuestas resumidas que la persona no haya dicho.

## Intercambio y comentarios

Los dos están moderados. En «Configuración del sitio» se pueden desactivar en cualquier momento. Los formularios tienen protección contra spam y avisan si detectan cédulas, teléfonos, direcciones o datos clínicos.

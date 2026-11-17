# Modelo de datos

Todos los contenidos que se pueden moderar heredan de `ModeratedContent` (`apps/core/models.py`). Ese modelo base tiene estos campos:

- título y descripción;
- estado: borrador → pendiente → en revisión → cambios solicitados → aprobado / rechazado / retirado / archivado;
- origen: información educativa revisada, institucional, aporte de la comunidad o pendiente de verificación;
- autor y fechas;
- quién lo revisó y su comentario;
- destacado y número de visitas.

Solo el contenido **aprobado** es público (`objects.public()`). Todo cambio de estado pasa por `apps/moderation/services.transition()`, que también deja el registro en el historial y envía las notificaciones. Antes de aprobar, se ejecuta `publication_problems()`: si a un contenido le faltan elementos obligatorios, no se puede publicar.

| Aplicación | Modelo | Campos principales | Requisitos para publicarse |
|---|---|---|---|
| core | Topic (tema) | nombre, slug, pictograma, orden | — |
| core | Source (fuente) | cita APA, cita corta, URL, tipo (legal/oficial/científica/prensa/recurso), fecha de consulta, temas | — |
| core | SiteConfig | aviso, correo de contacto, comentarios activos, intercambio activo | — |
| learn | Capsule (cápsula) | tema, explicación, importancia, ejemplos, introducción práctica, recomendaciones, precauciones, gráfico (o imagen con texto alternativo), acción sugerida, fecha de revisión, revisión profesional; M2M: actividades, materiales, videos, fuentes, temas | al menos 1 fuente y 1 recurso práctico; texto alternativo si tiene imagen |
| learn | FAQ | pregunta, respuesta, enlace | — |
| practice | Pictogram | código, etiqueta, categoría, imagen opcional, crédito, licencia | — |
| practice | Activity (actividad) | tipo, edad, duración, lugar, objetivo, materiales, pasos, adaptaciones, precauciones; M2M: materiales, temas, fuentes | — |
| practice | Material + MaterialItem | tipo, diseño de impresión, modo de uso, preguntas de ficha, archivo, enlace, autoría, licencia, derechos confirmados; ítems con pictograma y texto | autoría y derechos confirmados; archivo, enlace o ítems |
| practice | Video | publicador, URL o ID de YouTube, idioma, subtítulos, por qué se recomienda, fecha de revisión | URL o video, y fecha de revisión |
| directory | Institution (institución) | tipo, servicios, inclusión, población, provincia, cantón, contactos, costo, **base de verificación** (acreditación / autorización / registro / información pública / autodescripción / pendiente), enlace de respaldo, nota, documento privado, fecha de última revisión | base distinta de «pendiente», respaldo y fecha |
| interviews | Interview + InterviewQuestion | organización, persona, fecha, video o transcripción, resumen, referencias, autorización y documento privado; preguntas por eje con respuesta | todos los datos, el medio o la transcripción, la autorización y las respuestas |
| exchange | ExchangeItem | ofrezco/busco, tipo, estado, provincia, cantón, contacto autorizado, entrega, **disponibilidad** (disponible/reservado/finalizado), seguridad confirmada | — (la moderación es humana) |
| comments | Comment | cápsula, texto | — (la moderación es humana) |
| moderation | ModerationAction | objeto, actor, acción, estado anterior y nuevo, comentario | — |
| reports | Report | objeto, motivo, detalle, estado | — |
| accounts | User (ingresa con correo) + Profile | nombre visible, tipo de participación | — |

Sobre los archivos:

- Los archivos subidos se validan por extensión y por su contenido real (PDF, PNG o JPG; máximo 5 MB).
- Se sirven a través de `core:file`. Los públicos se muestran solo si el contenido está aprobado.
- Los privados (respaldos de instituciones y autorizaciones de entrevistas) solo los ven su autor y el equipo de moderación.

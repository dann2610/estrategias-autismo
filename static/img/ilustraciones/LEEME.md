# Imágenes del sitio

Las **fotografías** entregadas por el equipo están en `static/img/fotos/`. La imagen de cada tarjeta se asigna en `apps/core/templatetags/ui.py` (`FOTOS_TEMA` por tema de cápsula y `FOTOS_MODULO` por tipo de contenido): si se crea una cápsula o actividad nueva desde la administración, recibe su imagen automáticamente.

## Ilustraciones

Estas ilustraciones son originales del proyecto (no tienen derechos de terceros).

| Archivo | Dónde aparece |
|---|---|
| `familia.svg` | Carrusel del inicio (1), puerta «Comprender», página «Comprender el autismo» |
| `aula.svg` | Carrusel del inicio (2), «Sobre el proyecto» |
| `juego.svg` | Carrusel del inicio (3), «Actividades» |
| `comunidad.svg` | Carrusel del inicio (4), «Orientación y comunidad», «Intercambio», «Participar» |
| `agenda.svg` | Puerta «Actividades», «Actividades y recursos», «Apoyos visuales», «Pictogramas» |
| `conversacion.svg` | Puerta «Orientación», «Directorio», «Preguntas frecuentes», «Entrevistas» |

## Cómo poner fotos reales en el carrusel

1. Copia las fotos (JPG o WEBP, horizontales, idealmente 1200 × 780 px) en esta carpeta.
   Ejemplo: `foto-taller.jpg`.
2. Abre `templates/core/home.html` y, en el bloque «Carrusel de imágenes», cambia
   `img/ilustraciones/familia.svg` por `img/ilustraciones/foto-taller.jpg`.
3. Cambia también el texto `alt` para describir la foto.
4. Usa solo fotos propias o con autorización firmada. Si aparecen niñas o niños,
   se necesita el consentimiento de su madre, padre o representante y es mejor
   que no se vea su rostro.

"""
Carga el contenido inicial verificado del proyecto (idempotente: no duplica si se ejecuta de nuevo).

- Cápsulas, actividades y materiales redactados por el equipo a partir de fuentes realmente consultadas.
  Quedan publicados, con la indicación «pendiente de revisión profesional» hasta que un profesional los revise.
- Directorio: solo instituciones con fuente pública verificable.
- Entrevista: en preparación («contenido próximamente»), sin declaraciones inventadas.
- No se crean publicaciones de intercambio, comentarios ni testimonios.

Uso:  python manage.py cargar_contenido
      python manage.py cargar_contenido --usuarios-demo   (solo con DJANGO_DEBUG=True)
"""
import datetime as dt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.choices import Origin, Status
from apps.core.models import SiteConfig, Source, Topic
from apps.directory.models import Institution
from apps.interviews.models import Interview, InterviewQuestion
from apps.learn.models import FAQ, Capsule
from apps.moderation.models import ModerationAction
from apps.moderation.services import record
from apps.practice.models import Activity, Material, MaterialItem, Pictogram, Video

TODAY = dt.date(2026, 10, 28)

TOPICS = [
    ("diversidad", "Diversidad y fortalezas", "1f308", "Cada persona autista tiene un perfil propio de fortalezas y necesidades."),
    ("comunicacion", "Comunicación", "1f4ac", "Formas de comunicarse e interactuar, con y sin palabras."),
    ("rutinas", "Rutinas y anticipación", "1f5d3", "Agendas visuales y estrategias para que el día sea predecible."),
    ("emociones", "Emociones y calma", "1f600", "Reconocer emociones y atravesar momentos de sobrecarga."),
    ("sensorial", "Sensorialidad", "1f3a7", "Diferencias en la percepción de sonidos, luces, texturas y temperatura."),
    ("juego", "Juego y aprendizaje", "1f9f8", "Juegos sencillos para aprender y compartir."),
    ("autonomia", "Autonomía", "1f9fc", "Aprender paso a paso las tareas de la vida diaria."),
    ("escuela", "Escuela e inclusión", "1f3eb", "Adaptaciones para el aula y trabajo conjunto entre familia y escuela."),
    ("derechos", "Derechos", "2696", "Normas y trámites oficiales en Ecuador."),
    ("apoyo", "Buscar orientación", "1f9ed", "Cómo y dónde buscar orientación y ayuda profesional."),
]

SOURCES = {
    "oms": dict(short="(OMS, 2025)", kind="oficial", topics=["diversidad", "apoyo"],
                citation="Organización Mundial de la Salud. (2025). Autismo [Nota descriptiva].",
                url="https://www.who.int/es/news-room/fact-sheets/detail/autism-spectrum-disorders",
                notes="Prevalencia mundial estimada para 2021, diversidad de capacidades y necesidades, afecciones concurrentes."),
    "nimh": dict(short="(NIMH, 2025)", kind="oficial", topics=["comunicacion", "sensorial", "apoyo"],
                 citation="National Institute of Mental Health. (2025). Trastornos del espectro autista. Institutos Nacionales de la Salud de EE. UU.",
                 url="https://nimh.nih.gov/health/publications/espanol/trastornos-del-espectro-autista",
                 notes="Señales en comunicación, interacción y conductas; diferencias sensoriales; fortalezas; consejos para familias."),
    "cdc": dict(short="(CDC, 2026)", kind="oficial", topics=["apoyo"],
                citation="Centros para el Control y la Prevención de Enfermedades. (2026). Indicadores del desarrollo de los CDC. Aprenda los signos. Reaccione pronto.",
                url="https://cdc.gov/act-early/es/milestones/index.html",
                notes="Recomendación de no esperar y hablar con el médico ante preocupaciones o pérdida de habilidades. Contexto de EE. UU."),
    "buffle24": dict(short="(Buffle et al., 2024)", kind="cientifica", topics=["apoyo"],
                     citation="Buffle, P., Cavadini, T., Ortega, M. de L., Armijos, C., Soto, P., Gentaz, E., & Crane, L. (2024). Journeys towards accessing an autism diagnosis and associated support: A survey of families of autistic children in Ecuador. Autism. https://doi.org/10.1177/13623613241281029",
                     url="https://doi.org/10.1177/13623613241281029",
                     notes="Encuesta a 767 familias ecuatorianas sobre el camino al diagnóstico."),
    "ops": dict(short="(OPS, s. f.)", kind="oficial", topics=["comunicacion", "rutinas", "emociones"],
                citation="Organización Panamericana de la Salud. (s. f.). Capacitación de los cuidadores para transformar la vida de los niños.",
                url="https://www.paho.org/es/historias/capacitacion-cuidadores-para-transformar-vida-ninos",
                notes="Programa de la OMS: juego y rutinas como oportunidades de aprendizaje, comunicación y manejo de conductas desafiantes."),
    "lod": dict(short="(Asamblea Nacional del Ecuador, 2012)", kind="legal", topics=["derechos", "escuela"],
                citation="Asamblea Nacional del Ecuador. (2012). Ley Orgánica de Discapacidades. Registro Oficial Suplemento 796, 25 de septiembre de 2012 (última reforma: Registro Oficial Suplemento 481, 6 de mayo de 2019).",
                url="https://www.trabajo.gob.ec/wp-content/uploads/2024/01/LEY-ORGANICA-DE-DISCAPACIDADES.pdf",
                notes="Artículos citados: 1 (objeto), 6 (persona con discapacidad), 9 (calificación), 27 (educación) y 28 (educación inclusiva). Texto publicado por el Ministerio del Trabajo."),
    "msp": dict(short="(Ministerio de Salud Pública del Ecuador, 2026)", kind="legal", topics=["derechos", "apoyo"],
                citation="Ministerio de Salud Pública del Ecuador. (2026). Emisión de certificado de calificación o recalificación de discapacidad en el establecimiento de salud [Ficha de trámite]. Gob.ec.",
                url="https://www.gob.ec/msp/tramites/emision-certificado-calificacion-recalificacion-discapacidad-establecimiento-salud",
                notes="Requisitos, gratuidad y canal de atención. Ficha actualizada el 15 de enero de 2026."),
    "universo": dict(short="(El Universo, 2024)", kind="prensa", topics=["derechos"],
                     citation="El Universo. (2024, 12 de noviembre). [Nota sobre el documento que reemplaza al carné de discapacidad desde 2025]. El Universo.",
                     url="https://www.eluniverso.com/noticias/ecuador/como-sacar-el-documento-que-reemplaza-al-carne-de-discapacidad-nota/",
                     notes="Desde el 1 de enero de 2025 la cédula registra el porcentaje de discapacidad y reemplaza al carné."),
    "mercurio": dict(short="(Campoverde, 2024)", kind="prensa", topics=["escuela"],
                     citation="Campoverde, F. (2024, 2 de abril). Autismo en Ecuador: 4.179 estudiantes del sistema público tienen este trastorno. El Mercurio.",
                     url="https://elmercurio.com.ec/actualidad/2024/04/02/autismo-dia-mundial-ecuador/",
                     notes="Cifra del Ministerio de Educación para 2024."),
    "arasaac": dict(short="(Gobierno de Aragón, s. f.)", kind="recurso", topics=["comunicacion"],
                    citation="Gobierno de Aragón. (s. f.). ARASAAC: Portal Aragonés de la Comunicación Aumentativa y Alternativa. Pictogramas de Sergio Palao, licencia CC BY-NC-SA.",
                    url="https://arasaac.org", notes="Banco de pictogramas recomendado; se enlaza, no se copia."),
    "aesp": dict(short="(Autismo España, 2023)", kind="recurso", topics=["diversidad"],
                 citation="Autismo España. (2023). ¿Qué es el trastorno del espectro del autismo (TEA)? [Infografía].",
                 url="https://autismo.org.es/wp-content/uploads/2023/04/2023_InfografiaGeneralTEA_A5_AutismoEspana.pdf",
                 notes="Discapacidad invisible, variabilidad entre personas, posible coexistencia con otras condiciones y papel de la familia."),
    "wcag": dict(short="(W3C, 2024)", kind="recurso", topics=[],
                 citation="World Wide Web Consortium. (2024). Web Content Accessibility Guidelines (WCAG) 2.2. W3C Recommendation.",
                 url="https://www.w3.org/TR/WCAG22/", notes="Referencia para el diseño accesible del sitio."),
}

PICTOGRAMS = [
    ("rutina", [("2600", "Despertar"), ("1f6bd", "Ir al baño"), ("1f6bf", "Bañarse"), ("1faa5", "Cepillarse los dientes"),
                ("1f9fc", "Lavarse las manos"), ("1f455", "Vestirse"), ("1f963", "Desayunar"), ("1f37d", "Comer"),
                ("1f392", "Preparar la mochila"), ("1f4da", "Hacer tareas"), ("1f4d6", "Leer un cuento"),
                ("1f6cf", "Dormir"), ("1f9fa", "Guardar los juguetes"), ("1f6b0", "Abrir el agua"),
                ("1f450", "Frotar las manos"), ("1f9fb", "Secar las manos"), ("1f319", "Noche")]),
    ("emocion", [("1f600", "Feliz"), ("1f622", "Triste"), ("1f620", "Enojado"), ("1f628", "Asustado"),
                 ("1f60c", "Tranquilo"), ("1f634", "Cansado"), ("1f632", "Sorprendido"), ("1f623", "Incómodo"),
                 ("1f912", "Me siento mal")]),
    ("necesidad", [("1f4a7", "Agua"), ("1f34e", "Comida"), ("1f64b", "Ayuda"), ("23f8", "Pausa"), ("1f917", "Abrazo"),
                   ("1f3a7", "Audífonos"), ("1f507", "Silencio"), ("23f3", "Esperar"), ("2705", "Terminado"),
                   ("1f44d", "Sí"), ("1f44e", "No"), ("270b", "Alto")]),
    ("lugar", [("1f3eb", "Ir a la escuela"), ("1f3e0", "Volver a casa"), ("1f68c", "Bus"), ("1f697", "Auto"),
               ("1f333", "Parque"), ("1f6d2", "Supermercado"), ("1fa7a", "Médico"), ("1f9b7", "Dentista"),
               ("2702", "Corte de cabello"), ("1f382", "Cumpleaños")]),
    ("accion", [("1f9f8", "Jugar"), ("1f3a8", "Pintar"), ("1f3b5", "Música"), ("1f3c0", "Pelota"), ("1f3c3", "Correr"),
                ("1f4fa", "Ver televisión")]),
]

MATERIALS = {
    "manana": dict(title="Agenda visual: rutina de la mañana", kind="agenda", layout="secuencia", featured=True,
                   description="Siete pasos de la mañana, desde despertar hasta llegar a la escuela, para anticipar la salida de casa.",
                   items=["Despertar", "Ir al baño", "Vestirse", "Desayunar", "Cepillarse los dientes", "Preparar la mochila", "Ir a la escuela"],
                   how="Imprime la agenda y recorta los pasos si quieres moverlos.\nQuita los pasos que no correspondan a tu rutina; también puedes crear la tuya con el creador de agendas.\nPégala a la altura de los ojos de la niña o el niño.\nRecórranla juntos antes de empezar y marquen cada paso al terminarlo.",
                   topics=["rutinas", "autonomia"]),
    "noche": dict(title="Agenda visual: rutina de la noche", kind="agenda", layout="secuencia",
                  description="Cinco pasos para la noche que ayudan a anticipar la hora de dormir.",
                  items=["Comer", "Bañarse", "Cepillarse los dientes", "Leer un cuento", "Dormir"],
                  how="Imprime la agenda y colócala en el dormitorio o en el baño.\nRepásenla después de la cena.\nMantén el mismo orden todas las noches mientras se acostumbra.",
                  topics=["rutinas"]),
    "manos": dict(title="Secuencia: lavarse las manos", kind="secuencia", layout="secuencia",
                  description="Cinco pasos ilustrados para aprender a lavarse las manos con autonomía.",
                  items=[("Abrir el agua", None), ("Lavarse las manos", "Poner jabón"), ("Frotar las manos", None), ("Agua", "Enjuagar"), ("Secar las manos", None)],
                  how="Imprime y, si puedes, plastifica la secuencia.\nPégala junto al lavamanos, a la altura de sus ojos.\nSeñala cada paso mientras lo hacen juntos.",
                  topics=["autonomia", "rutinas"]),
    "emociones": dict(title="Tarjetas de emociones", kind="tarjetas", layout="cuadricula", featured=True,
                      description="Nueve tarjetas para reconocer y nombrar emociones en momentos tranquilos.",
                      items=["Feliz", "Triste", "Enojado", "Asustado", "Tranquilo", "Cansado", "Sorprendido", "Incómodo", "Me siento mal"],
                      how="Imprime y recorta las tarjetas.\nEmpieza con dos emociones muy diferentes y agrega otras poco a poco.\nÚsalas en momentos tranquilos, no durante una crisis.",
                      topics=["emociones"]),
    "necesidades": dict(title="Tablero de necesidades básicas", kind="tablero", layout="cuadricula", featured=True,
                        description="Nueve pictogramas para pedir agua, comida, ayuda, una pausa o decir sí y no.",
                        items=["Agua", "Comida", "Ir al baño", "Ayuda", "Pausa", "Abrazo", "Audífonos", "Sí", "No"],
                        how="Imprime el tablero y déjalo siempre en el mismo lugar, a su alcance.\nModela su uso: señala la imagen mientras dices la palabra.\nResponde de inmediato cuando la niña o el niño señale una imagen.",
                        topics=["comunicacion"]),
    "primero": dict(title="Tablero Primero / Después", kind="primero", layout="primero",
                    description="Muestra una tarea y lo que viene a continuación para facilitar las transiciones.",
                    items=["Hacer tareas", "Jugar"],
                    how="Imprime el tablero; el ejemplo muestra «hacer tareas» y después «jugar».\nPara otras situaciones, recorta pictogramas del banco y pégalos encima.\nCumple siempre lo que muestra el «después».",
                    topics=["rutinas", "escuela"]),
    "pausa": dict(title="Tarjeta: necesito una pausa", kind="tarjetas", layout="tarjeta",
                  description="Una tarjeta grande para pedir una pausa cuando algo abruma.",
                  items=[("Pausa", "Necesito una pausa")],
                  how="Imprime la tarjeta y déjala en el rincón de calma o en su mochila.\nPractica su uso en momentos tranquilos.\nCuando la muestre, respeta su pedido y acompaña sin insistir.",
                  topics=["emociones", "sensorial"]),
    "memoria": dict(title="Juego de memoria: la rutina", kind="juego", layout="pares",
                    description="Pares de pictogramas de la vida diaria para jugar por turnos.",
                    items=["Cepillarse los dientes", "Bañarse", "Comer", "Dormir", "Jugar", "Leer un cuento"],
                    how="Imprime la hoja; cada pictograma aparece dos veces.\nRecorta las tarjetas y colócalas boca abajo.\nSigue los pasos de la actividad «Memoria de la rutina».",
                    topics=["juego"]),
    "ficha": dict(title="Ficha: lo que me ayuda", kind="ficha", layout="ficha", featured=True,
                  description="Una ficha para describir lo que le gusta, lo que le calma, lo que le molesta y cómo se comunica.",
                  prompts="Me gusta y me interesa…\nMe calma…\nMe molesta o me abruma…\nAsí me comunico…\nAsí pido ayuda o una pausa…\nLo que hago muy bien…\nAlgo que estoy aprendiendo…",
                  how="Complétala en familia y, cuando sea posible, con la niña o el niño.\nCompártela con la escuela al inicio del año y con los profesionales.\nActualízala cada cierto tiempo.",
                  topics=["diversidad", "escuela"]),
    "registro": dict(title="Registro de observaciones para la consulta", kind="ficha", layout="ficha",
                     description="Una hoja para anotar lo que preocupa y llegar preparados a la consulta profesional.",
                     prompts="¿Qué observo? Describe la situación con ejemplos.\n¿Desde cuándo lo noto y con qué frecuencia?\n¿En qué lugares o momentos ocurre (casa, escuela, salidas)?\n¿Qué parece empeorarlo y qué ayuda?\n¿Ha perdido alguna habilidad que antes tenía?\nPreguntas que quiero hacer al profesional",
                     how="Anota durante una o dos semanas, con fechas.\nLleva la hoja a la consulta junto con los informes anteriores.\nGuarda una copia en la carpeta de documentos.",
                     topics=["apoyo"]),
}

ACTIVITIES = {
    "agenda": dict(title="Agenda visual de la mañana", kind="rutinas", age="todas", duration="15", place="hogar", featured=True,
                   description="Anticipar con imágenes los pasos de la mañana para que salir de casa sea más tranquilo.",
                   objective="Anticipar los pasos de la mañana para que la salida de casa sea más predecible.",
                   materials="Agenda visual impresa o creada en el sitio\nCinta adhesiva o velcro\nUn sobre o caja para los pasos terminados",
                   steps="Elige los pasos reales de la mañana en tu casa, entre 5 y 7.\nImprime la agenda y pégala a la altura de los ojos de la niña o el niño.\nCada mañana, antes de empezar, recórranla juntos señalando cada imagen.\nAl terminar un paso, márquenlo o pongan la imagen en el sobre de «terminado».\nSi algo cambia ese día, muéstralo en la agenda antes de que ocurra.",
                   adaptations="Para niñas y niños pequeños, empieza con 3 pasos.\nSi entiende mejor las fotos que los dibujos, usa fotografías de sus propias cosas.\nPara mayores, agrega la hora o deja que escriba los pasos.",
                   precautions="Introduce la agenda en un día tranquilo, no en uno lleno de cambios.\nNo la uses como castigo.\nSi la agenda le genera ansiedad, reduce los pasos o pausa su uso y consulta a un profesional.",
                   materials_rel=["manana"], topics=["rutinas", "autonomia"], sources=["ops", "nimh"]),
    "primero": dict(title="Primero y después para las transiciones", kind="rutinas", age="todas", duration="5", place="ambos",
                    description="Mostrar qué viene a continuación para pasar de una actividad a otra con menos tensión.",
                    objective="Facilitar el paso de una actividad a otra mostrando qué viene a continuación.",
                    materials="Tablero Primero / Después impreso\nPictogramas de las actividades",
                    steps="Coloca en «Primero» la actividad que toca ahora y en «Después» una actividad que le guste.\nMuestra el tablero y di una frase corta: «Primero guardar, después cena».\nAvisa unos minutos antes de terminar la actividad actual.\nCuando termine el «primero», señala el «después» y cúmplelo.",
                    adaptations="Usa un reloj de arena o un temporizador para mostrar cuánto falta.\nEn el aula puede usarse con todo el grupo.",
                    precautions="Cumple siempre el «después» prometido; si no, el tablero pierde sentido.\nNo lo uses para negociar ni para amenazar.",
                    materials_rel=["primero"], topics=["rutinas", "escuela"], sources=["nimh"]),
    "elegir": dict(title="¿Esto o aquello? Elegir con tarjetas", kind="comunicacion", age="todas", duration="5", place="ambos", featured=True,
                   description="Ofrecer dos opciones con imágenes para que la niña o el niño exprese lo que prefiere.",
                   objective="Ofrecer una forma de expresar preferencias mediante imágenes.",
                   materials="Tablero de necesidades o dos tarjetas con pictogramas\nLos objetos reales que se ofrecen",
                   steps="En un momento cotidiano, como la merienda, muestra dos tarjetas y los dos objetos reales.\nNombra cada opción mientras la señalas: «¿Agua o jugo?».\nEspera a que mire, señale o toque una tarjeta.\nEntrega de inmediato lo que eligió y nómbralo: «Agua».\nRepite en otros momentos del día con opciones distintas.",
                   adaptations="Empieza con dos opciones que le gusten.\nSi aún no señala, acepta la mirada o el acercamiento como elección.\nCuando domine dos opciones, prueba con tres.",
                   precautions="No retengas lo que necesita para obligarle a pedirlo.\nRespeta un «no» o el rechazo de ambas opciones.",
                   materials_rel=["necesidades"], topics=["comunicacion"], sources=["ops", "arasaac"]),
    "turnos": dict(title="Mi turno, tu turno", kind="juego", age="todas", duration="5", place="ambos",
                   description="Un juego de pelota para practicar el ir y venir de la interacción.",
                   objective="Practicar el ir y venir de la interacción a través de un juego sencillo.",
                   materials="Una pelota blanda o un carrito",
                   steps="Siéntense frente a frente, cerca.\nDi «mi turno» y haz rodar la pelota hacia la niña o el niño.\nDi «tu turno» y espera a que la devuelva; ayúdale con un gesto si lo necesita.\nRepite varias veces y celebra cada intercambio.\nCuando el juego funcione, invita a otra persona a participar.",
                   adaptations="Usa un objeto de su interés para aumentar la motivación.\nEn el aula, practíquenlo en grupos pequeños.\nCon niñas y niños mayores, usen juegos de mesa sencillos con turnos.",
                   precautions="Termina el juego antes de que se canse o se frustre.\nSi un objeto le molesta por su ruido o su textura, cámbialo.",
                   materials_rel=[], topics=["juego", "comunicacion"], sources=["ops"]),
    "emociones": dict(title="¿Cómo me siento? Tarjetas de emociones", kind="emociones", age="todas", duration="15", place="ambos", featured=True,
                      description="Reconocer y nombrar emociones con tarjetas, en momentos tranquilos.",
                      objective="Reconocer y nombrar emociones básicas en momentos tranquilos.",
                      materials="Tarjetas de emociones impresas\nUn espejo (opcional)",
                      steps="Elige un momento tranquilo, no durante una crisis.\nMuestra una tarjeta, nombra la emoción y haz la expresión frente al espejo.\nRelaciona cada emoción con una situación conocida: «Feliz, como cuando vamos al parque».\nInvita a la niña o al niño a elegir la tarjeta que muestra cómo se siente hoy.\nRepitan durante varios días, con pocas emociones a la vez.",
                      adaptations="Empieza con dos emociones muy diferentes: feliz y triste.\nUsa fotografías de la familia o de personajes que reconozca.\nCon mayores, agreguen una escala de intensidad: un poco, bastante, mucho.",
                      precautions="No obligues a mirar a los ojos ni a imitar expresiones si le incomoda.\nNo uses las tarjetas para pedir explicaciones en medio de una crisis.",
                      materials_rel=["emociones"], topics=["emociones"], sources=["ops"]),
    "calma": dict(title="Un rincón de calma", kind="emociones", age="todas", duration="30", place="ambos",
                  description="Preparar juntos un lugar tranquilo para regularse cuando algo abruma.",
                  objective="Preparar un lugar al que la niña o el niño pueda ir para regularse cuando algo le abruma.",
                  materials="Un espacio con poco ruido y poca luz\nCojín o colchoneta\nObjetos que le calmen: peluche, audífonos, libro\nTarjeta «Necesito una pausa»",
                  steps="Elijan juntos un lugar tranquilo, lejos de pasillos y ruidos.\nColoquen pocos objetos que la niña o el niño elija.\nPresenten el rincón en un momento tranquilo y practiquen ir a él.\nAcuerden cómo pedirlo: con la tarjeta, un gesto o una palabra.\nCuando lo use, respeten su tiempo y acompañen sin insistir.",
                  adaptations="En el aula, puede ser una esquina con una alfombra y una cortina.\nSi no hay espacio, una caja con objetos de calma cumple una función parecida.",
                  precautions="El rincón no es un lugar de castigo ni de aislamiento.\nSupervisa siempre a niñas y niños pequeños.\nRevisa que los objetos sean seguros.",
                  materials_rel=["pausa", "emociones"], topics=["emociones", "sensorial", "escuela"], sources=["nimh", "ops"]),
    "manos": dict(title="Lavarse las manos paso a paso", kind="autonomia", age="todas", duration="5", place="ambos",
                  description="Aprender la secuencia de lavarse las manos con apoyo visual.",
                  objective="Aprender la secuencia de lavarse las manos con apoyo visual.",
                  materials="Secuencia «Lavarse las manos» impresa y, si es posible, plastificada\nJabón y toalla",
                  steps="Pega la secuencia junto al lavamanos, a la altura de sus ojos.\nRealicen cada paso juntos mientras señalas la imagen.\nPoco a poco, señala la imagen y deja que haga el paso por su cuenta.\nCelebra cuando complete la secuencia.",
                  adaptations="Si el agua fría o el jabón le molestan, ajusta la temperatura o prueba otro jabón.\nCon mayores, retira las imágenes a medida que aprende.",
                  precautions="Supervisa la temperatura del agua.\nNo apures: la autonomía se construye con práctica.",
                  materials_rel=["manos"], topics=["autonomia", "rutinas"], sources=["ops"]),
    "memoria": dict(title="Memoria de la rutina", kind="juego", age="6-8", duration="15", place="ambos",
                    description="Un juego de memoria con pictogramas de la vida diaria para jugar por turnos.",
                    objective="Practicar la atención, la memoria visual y los turnos con pictogramas de la vida diaria.",
                    materials="Juego de memoria impreso\nTijeras",
                    steps="Recorta las tarjetas y colócalas boca abajo.\nPor turnos, levanten dos tarjetas y nombren lo que muestran.\nSi coinciden, se las queda quien las encontró; si no, se vuelven a tapar.\nEmpiecen con pocos pares y aumenten poco a poco.",
                    adaptations="Con más pequeños, jueguen con las tarjetas boca arriba buscando parejas.\nCon mayores, usen todas las tarjetas.",
                    precautions="Termina antes de que aparezca la frustración.\nRedondea las esquinas de las tarjetas al recortarlas.",
                    materials_rel=["memoria"], topics=["juego", "rutinas"], sources=[]),
    "aula": dict(title="Anticipar la jornada en el aula", kind="aula", age="todas", duration="5", place="escuela",
                 description="Revisar al inicio del día las actividades y los cambios previstos, con todo el grupo.",
                 objective="Que el grupo conozca al inicio del día las actividades y los cambios previstos.",
                 materials="Agenda visual del día en la pizarra, creada en el sitio\nUna tarjeta de «cambio» para imprevistos",
                 steps="Al iniciar la jornada, revisa la agenda con todo el grupo.\nSeñala cada actividad al comenzarla y márcala al terminar.\nSi hay un cambio, muéstralo en la agenda y explícalo con una frase corta.\nAntes de cada transición, avisa unos minutos antes.\nComparte con la familia la agenda de días especiales, como salidas o simulacros.",
                 adaptations="Para un estudiante que lo necesite, usa además una agenda individual en su pupitre.\nCombina imágenes con palabras escritas para quienes ya leen.",
                 precautions="Coordina con el Departamento de Consejería Estudiantil (DECE) y con la familia.\nNo expongas al estudiante frente al grupo por sus dificultades.",
                 materials_rel=["manana"], topics=["escuela", "rutinas"], sources=["lod"]),
}

CAPSULES = [
    dict(key="que-es", order=1, theme="que-es", visual="que_es", featured=True,
         title="¿Qué es el trastorno del espectro autista?",
         description="Una explicación sencilla de qué es el autismo, por qué se habla de un espectro y qué no es.",
         explanation="El trastorno del espectro autista (TEA) es una condición del neurodesarrollo: tiene que ver con la forma en que el cerebro se desarrolla y procesa la información. Influye en cómo una persona se comunica, se relaciona con los demás, aprende y percibe su entorno (NIMH, 2025).\n\nSe habla de «espectro» porque las características y las necesidades de apoyo varían mucho de una persona a otra y pueden cambiar con el tiempo. Algunas personas autistas viven con bastante independencia; otras necesitan apoyos durante toda la vida (OMS, 2025).\n\nLas señales suelen aparecer en los primeros años y se agrupan en dos áreas: la comunicación y la interacción social, y los intereses, las conductas repetitivas y la forma de procesar los estímulos sensoriales. Muchas personas autistas tienen además fortalezas, como aprender con gran detalle o una buena memoria visual (NIMH, 2025).\n\nEl autismo no se ve a simple vista: no tiene rasgos físicos que lo identifiquen, por eso se le describe como una discapacidad invisible (Autismo España, 2023). Según la OMS (2025), en 2021 aproximadamente una de cada 127 personas en el mundo era autista.",
         importance="Comprender qué es el autismo cambia la forma de interpretar lo que hace una niña o un niño. Una conducta que parece un capricho puede ser una manera de comunicar malestar, de protegerse de un ruido o de pedir que algo sea predecible.\n\nPara las familias, esta comprensión reduce la culpa y ayuda a buscar apoyos. Para los docentes, permite anticipar situaciones y adaptar el aula antes de que aparezcan las dificultades.",
         examples="Un niño de 4 años no voltea cuando lo llaman por su nombre, pero reconoce enseguida la música de su programa favorito.\nUna niña habla mucho sobre los dinosaurios y le cuesta cambiar de tema durante el recreo.\nUn niño se tapa los oídos y llora cuando suena la licuadora o cuando hay mucha gente en el mercado.\nUna niña ordena sus juguetes en filas y se molesta si alguien las desordena.",
         practice="Entender estas características es el primer paso. El siguiente es ofrecer apoyos que hagan el día más predecible y comprensible: empieza por una agenda visual sencilla y por un tablero para expresar necesidades.",
         activities=["agenda"], materials=["necesidades", "ficha"], videos=[], action="",
         recommendations="Observa qué le interesa, qué le calma y qué le molesta: esa información es valiosa.\nUsa frases cortas y claras, acompañadas de gestos o imágenes.\nCelebra sus fortalezas y avances, por pequeños que parezcan.\nBusca información en fuentes confiables y desconfía de quien prometa curas.",
         precautions="Esta cápsula no sirve para diagnosticar; solo un equipo profesional puede hacerlo.\nNo compares a tu hija o hijo con otras personas autistas: cada perfil es distinto.\nEn lugar de etiquetas como «leve» o «grave», es más útil hablar de los apoyos que necesita.",
         sources=["nimh", "oms", "aesp"], topics=["diversidad", "comunicacion"]),
    dict(key="diversidad", order=2, theme="diversidad", visual="perfil",
         title="Diversidad: fortalezas y necesidades de apoyo",
         description="Por qué dos niñas o niños autistas pueden ser muy diferentes y cómo describir el perfil de cada uno.",
         explanation="Dos niñas o niños con el mismo diagnóstico pueden ser muy diferentes. Uno puede hablar con fluidez y tener mucha dificultad con los cambios de plan; otro puede comunicarse sin palabras y adaptarse bien a una nueva rutina. Las capacidades y las necesidades de las personas autistas varían y pueden evolucionar con el tiempo (OMS, 2025).\n\nEn lugar de pensar en una línea que va de «poco» a «mucho» autismo, es más útil pensar en un perfil: en qué situaciones la persona se desenvuelve con facilidad y en cuáles necesita más apoyo. Ese perfil cambia con la edad, el entorno y los apoyos que recibe.\n\nEl autismo puede presentarse junto a otras condiciones, como epilepsia, ansiedad o trastorno por déficit de atención con hiperactividad (OMS, 2025), y en algunos casos junto a discapacidad intelectual o trastornos del lenguaje (Autismo España, 2023). Conocerlas ayuda a entender mejor las necesidades de cada persona.",
         importance="Conocer el perfil de la niña o el niño permite elegir apoyos a su medida, en lugar de aplicar la misma receta a todos. También ayuda a reconocer sus fortalezas, que suelen ser la mejor puerta de entrada para aprender.\n\nPara la escuela, contar con una descripción clara de lo que le ayuda y de lo que le cuesta facilita planificar adaptaciones y evita malentendidos.",
         examples="Una niña lee palabras desde muy pequeña, pero se angustia si cambia el camino a la escuela.\nUn niño no usa palabras para pedir, pero arma rompecabezas complejos con facilidad.\nUna niña conversa con adultos sobre su tema favorito, pero le cuesta unirse al juego de otros niños.\nUn niño tolera bien el ruido del recreo, pero necesita ayuda para vestirse.",
         practice="Una forma práctica de describir el perfil es completar una ficha con lo que le gusta, lo que le calma, lo que le molesta y cómo se comunica. Esa ficha se puede compartir con la escuela y con los profesionales. Para las tareas que aún le cuestan, una secuencia visual puede ayudar.",
         activities=["manos", "memoria"], materials=["ficha"], videos=[], action="",
         recommendations="Anota sus fortalezas e intereses: sirven para motivar el aprendizaje.\nActualiza la ficha cada cierto tiempo, porque las necesidades cambian.\nCuando sea posible, pregunta a la niña o al niño qué le gusta y qué le molesta.\nComparte la información con docentes y profesionales para trabajar en la misma dirección.",
         precautions="Evita suponer lo que puede o no puede hacer solo por el diagnóstico.\nNo describas a la persona únicamente por sus dificultades.\nSi notas que pierde habilidades que ya tenía, consulta pronto a un profesional.",
         sources=["oms", "aesp", "cdc"], topics=["diversidad", "autonomia"]),
    dict(key="comunicacion", order=3, theme="comunicacion", visual="comunicacion",
         title="Comunicación e interacción social",
         description="Las distintas formas de comunicarse y cómo los apoyos visuales pueden facilitar la comprensión y la expresión.",
         explanation="Comunicarse es mucho más que hablar. Algunas personas autistas hablan con fluidez; otras usan pocas palabras, repiten frases que escucharon (ecolalia) o se comunican con gestos, imágenes o dispositivos (NIMH, 2025). Todas esas formas son válidas.\n\nEn la interacción social pueden aparecer diferencias como mirar poco a los ojos o tener dificultad para seguir una conversación o entender lo que otra persona piensa o siente (NIMH, 2025). Eso no significa falta de interés por los demás: muchas veces la persona quiere relacionarse, pero lo hace de otra manera.\n\nLos apoyos visuales, como los pictogramas, ayudan a comprender y a expresarse, porque una imagen permanece a la vista mientras que las palabras desaparecen en cuanto se dicen. Existen bancos gratuitos de pictogramas pensados para la comunicación aumentativa (Gobierno de Aragón, s. f.).",
         importance="Cuando una niña o un niño no logra comunicar lo que necesita, la frustración puede convertirse en llanto, gritos o golpes. Ofrecerle otras formas de expresarse reduce esa frustración y le da más control sobre su día.\n\nEn casa y en la escuela, las rutinas diarias y el juego son oportunidades para practicar la comunicación sin presión, como propone el programa de capacitación para cuidadores de la OMS (OPS, s. f.).",
         examples="Lleva a un adulto de la mano hasta la refrigeradora para pedir agua.\nRepite frases de su dibujo animado favorito cuando está contento.\nSeñala una imagen para elegir entre jugar con bloques o con plastilina.\nEn el aula, responde mejor cuando la docente acompaña la instrucción con una tarjeta.",
         practice="Empieza ofreciendo opciones con imágenes en momentos cotidianos, como la merienda o el juego, y practica el ir y venir de una conversación con juegos de turnos.",
         activities=["elegir", "turnos"], materials=["necesidades"], videos=[], action="pictogramas",
         recommendations="Habla con frases cortas y espera su respuesta sin apurar.\nAcepta y celebra cualquier forma de comunicación, no solo las palabras.\nUsa siempre la misma imagen para la misma cosa.\nAprovecha sus intereses para iniciar intercambios.",
         precautions="No condiciones lo que necesita, como agua, comida o ir al baño, a que lo pida hablando.\nSi no usa palabras a la edad esperada o pierde palabras que ya decía, consulta al pediatra o a un profesional de terapia de lenguaje.\nEvita hablar de la niña o el niño frente a él como si no entendiera.",
         sources=["nimh", "ops", "arasaac"], topics=["comunicacion"]),
    dict(key="rutinas", order=4, theme="rutinas", visual="rutina",
         title="Rutinas, anticipación y apoyos visuales",
         description="Por qué anticipar lo que va a pasar reduce la ansiedad y cómo hacerlo con agendas visuales.",
         explanation="Muchas personas autistas sienten malestar ante cambios pequeños en la rutina (NIMH, 2025). No saber qué viene después puede generar ansiedad, y esa ansiedad puede expresarse con llanto, rigidez o rechazo.\n\nAnticipar significa avisar, antes de que ocurra, qué va a pasar, en qué orden y cuándo termina. Las agendas visuales muestran los pasos de una rutina con imágenes; el tablero «Primero / Después» muestra solo dos: una tarea y lo que viene a continuación.\n\nLas rutinas diarias, como vestirse o lavarse los dientes, también son oportunidades de aprendizaje y de comunicación (OPS, s. f.).",
         importance="Cuando el día es predecible, la niña o el niño puede concentrar su energía en aprender y participar, en lugar de estar en alerta. Las agendas también facilitan las transiciones, que suelen ser los momentos más difíciles: salir de casa, terminar de jugar o cambiar de actividad en el aula.\n\nSi la familia y la escuela usan los mismos apoyos visuales, se crea coherencia entre ambos espacios.",
         examples="Antes de salir, se repasa la agenda: baño, vestirse, desayunar, mochila, escuela.\nEn el aula, la docente señala en la agenda que después del recreo viene educación física.\nUn domingo distinto se anticipa con imágenes: primero visita a los abuelos, después parque.\nAntes de apagar la tableta se usa el tablero: primero guardar, después cena.",
         practice="Crea una agenda con los pasos de una rutina real de tu casa o de tu aula, o imprime una ya preparada. Para las transiciones cortas, usa el tablero Primero / Después.",
         activities=["agenda", "primero"], materials=["manana", "noche", "primero"], videos=[], action="agenda",
         recommendations="Empieza con una sola rutina y pocos pasos.\nMuestra la agenda antes de empezar y marca cada paso al terminarlo.\nAvisa los cambios con anticipación y muéstralos en la agenda.\nColoca la agenda a la altura de sus ojos.",
         precautions="Introduce los cambios de forma gradual; no reorganices todo el día de una vez.\nNo uses la agenda como castigo ni retires actividades agradables como amenaza.\nAlgunas niñas y niños entienden mejor los objetos reales o las fotografías que los dibujos: observa qué le funciona.",
         sources=["nimh", "ops"], topics=["rutinas"]),
    dict(key="emociones", order=5, theme="emociones", visual="emociones",
         title="Emociones, sensorialidad y momentos de sobrecarga",
         description="Qué es una sobrecarga, cómo reconocer sus señales y cómo acompañar con calma.",
         explanation="Muchas personas autistas perciben los estímulos de forma distinta: pueden ser más o menos sensibles a la luz, los sonidos, la ropa o la temperatura (NIMH, 2025). Un ruido que para otros es normal puede resultar doloroso.\n\nCuando se acumulan estímulos, cansancio o cambios inesperados, puede aparecer una sobrecarga: la persona ya no logra manejar lo que siente. A veces se expresa con llanto, gritos, intentos de salir del lugar o movimientos repetitivos. No es un berrinche para conseguir algo, sino una reacción ante algo que le supera.\n\nReconocer y nombrar las emociones, y contar con un lugar o una estrategia de calma, ayuda a prevenir y atravesar estos momentos. El programa de capacitación para cuidadores de la OMS incluye el manejo de conductas desafiantes y las estrategias de afrontamiento de los propios cuidadores (OPS, s. f.).",
         importance="Saber qué situaciones le abruman permite anticiparlas: elegir horarios con menos gente, llevar audífonos o prever pausas. Y cuando la sobrecarga ocurre, una respuesta calmada evita que la situación empeore.\n\nAcompañar también desgasta. Cuidar el propio bienestar, pedir ayuda y hablar con otras personas forma parte del acompañamiento.",
         examples="En una fiesta con música alta, se tapa los oídos y busca esconderse debajo de la mesa.\nRechaza una camiseta nueva por la textura de la tela.\nDespués de un día con muchos cambios, llora al llegar a casa aunque todo esté tranquilo.\nEn el aula, se calma cuando puede ir unos minutos al rincón tranquilo.",
         practice="Practica el reconocimiento de emociones con tarjetas en momentos tranquilos y prepara, junto con la niña o el niño, un rincón de calma y una tarjeta para pedir una pausa.",
         activities=["emociones", "calma"], materials=["emociones", "pausa"], videos=[], action="",
         recommendations="Observa y anota qué situaciones le abruman y qué le ayuda a calmarse.\nEn una sobrecarga, habla poco, con voz suave, y reduce los estímulos.\nOfrece un objeto o un lugar de calma que la niña o el niño haya elegido.\nDespués, cuando esté tranquilo, nombra lo que pasó sin reproches.",
         precautions="No castigues una sobrecarga ni exijas calma inmediata.\nNo lo toques ni lo abraces si en ese momento no lo acepta.\nSi hay riesgo de que se lastime o las crisis son muy frecuentes, consulta a un profesional.\nSi como cuidador sientes un agotamiento que no pasa, busca apoyo psicológico en tu centro de salud.",
         sources=["nimh", "ops"], topics=["emociones", "sensorial"]),
    dict(key="mitos", order=6, theme="mitos", visual="mitos",
         title="Mitos y realidades sobre el autismo",
         description="Ideas equivocadas frecuentes y qué dice la información verificada.",
         explanation="Alrededor del autismo circulan ideas equivocadas que generan culpa, estigma o falsas esperanzas. Conocer la información verificada ayuda a responder con calma a los comentarios de familiares, vecinos o personas de la escuela.\n\nEl autismo no se debe a la forma en que se cría a un niño: es una condición del neurodesarrollo (NIMH, 2025). Tampoco existe un solo tipo de autismo: las capacidades y las necesidades varían de una persona a otra (OMS, 2025).\n\nLas personas autistas sienten y expresan afecto, aunque a veces de maneras distintas a las esperadas. Y aunque el autismo acompaña a la persona toda la vida, los servicios y apoyos adecuados pueden mejorar su bienestar y su funcionamiento diario (NIMH, 2025).",
         importance="Los mitos influyen en cómo se trata a las personas autistas y a sus familias. Pueden llevar a culpar a los padres, a excluir a un niño de una actividad o a gastar dinero y esperanza en productos que prometen curas.\n\nResponder con información verificada protege a la familia y abre la puerta a la inclusión.",
         examples="Un familiar dice: «Eso se le quita con mano dura». Se puede explicar que el autismo no se debe a la crianza.\nEn la escuela comentan: «Pero si habla bien, no puede ser autista». Hay personas autistas que hablan con fluidez.\nEn redes sociales ofrecen un suplemento que «cura el autismo». Conviene desconfiar y consultar siempre a profesionales.\nAlguien pregunta si el niño quiere a su familia. Sí: muchas veces lo muestra de otra manera.",
         practice="Para ayudar a otras personas a comprender a tu hija o hijo, comparte una descripción concreta de lo que le ayuda y lo que le molesta. Suele ser más útil que cualquier explicación general.",
         activities=[], materials=["ficha"], videos=["cdc"], action="",
         recommendations="Responde con información breve y verificada, sin entrar en discusiones largas.\nComparte esta cápsula o sus fuentes con familiares y docentes.\nHabla de la persona antes que del diagnóstico.",
         precautions="Desconfía de quien prometa curas rápidas o venda productos «para el autismo».\nAntes de iniciar cualquier terapia, pregunta en qué evidencia se basa y consúltalo con profesionales.\nEvita compartir en redes información sin fuente.",
         sources=["nimh", "oms"], topics=["diversidad"]),
    dict(key="inclusion", order=7, theme="inclusion", visual="inclusion",
         title="Inclusión educativa: familia y escuela",
         description="Qué dice la ley, qué significa adaptar el aula y cómo trabajar juntos familia y escuela.",
         explanation="La inclusión educativa busca que todas las niñas y los niños aprendan juntos, con los apoyos que cada uno necesita. En Ecuador, la Ley Orgánica de Discapacidades establece que el Estado procurará que las personas con discapacidad puedan acceder, permanecer y culminar sus estudios, y que la autoridad educativa promoverá la inclusión de estudiantes con necesidades educativas especiales que requieran apoyos y adaptaciones (Asamblea Nacional del Ecuador, 2012, arts. 27-28).\n\nSegún cifras del Ministerio de Educación, en 2024 el sistema de educación pública registraba 4.179 estudiantes con autismo (Campoverde, 2024). Muchas aulas ya cuentan con estudiantes autistas y necesitan estrategias concretas.\n\nAdaptar no significa exigir menos, sino cambiar la forma de enseñar y de organizar el aula: anticipar la jornada, dar instrucciones claras, ofrecer pausas y usar apoyos visuales.",
         importance="La familia conoce a la niña o al niño mejor que nadie; la escuela observa cómo aprende y cómo se relaciona con otros. Cuando ambas comparten información y acuerdan estrategias comunes, los apoyos funcionan mejor en los dos espacios.\n\nPara los docentes, pequeños cambios en el aula pueden prevenir crisis y facilitar el aprendizaje de todo el grupo.",
         examples="Al inicio del año, la familia entrega una ficha con lo que calma y lo que molesta a su hijo.\nLa docente coloca la agenda del día en la pizarra y la revisa con todo el grupo.\nAntes de un simulacro, la escuela avisa a la familia para anticiparlo en casa.\nUn cuaderno de ida y vuelta permite contar cómo fue el día.",
         practice="Para el aula: anticipa la jornada con una agenda, ofrece un rincón de calma y practica los turnos con juegos sencillos. Para la familia: comparte la ficha «Lo que me ayuda» con la escuela.",
         activities=["aula", "calma", "turnos"], materials=["ficha"], videos=[], action="aula",
         recommendations="Pide una reunión al inicio del año con la docente y el Departamento de Consejería Estudiantil (DECE).\nAcuerden cómo se comunicarán y con qué frecuencia.\nUsen los mismos apoyos visuales en casa y en la escuela.\nRegistren los avances y revisen juntos lo que no funciona.",
         precautions="Las adaptaciones deben decidirse según las necesidades de cada estudiante, no solo por el diagnóstico.\nEvita exponer al estudiante frente al grupo por sus dificultades.\nPara trámites o reclamos, consulta la normativa vigente y las autoridades educativas de tu distrito.",
         sources=["lod", "mercurio"], topics=["escuela"]),
    dict(key="derechos", order=8, theme="derechos", visual="derechos",
         title="Derechos de las personas con discapacidad y sus familias",
         description="Lo que establece la Ley Orgánica de Discapacidades y cómo funciona la calificación de discapacidad en Ecuador.",
         explanation="En Ecuador, la Ley Orgánica de Discapacidades, publicada en el Registro Oficial Suplemento 796 del 25 de septiembre de 2012, tiene por objeto asegurar la prevención, la detección oportuna, la habilitación y la rehabilitación de la discapacidad, y garantizar el pleno ejercicio de los derechos de las personas con discapacidad (Asamblea Nacional del Ecuador, 2012, art. 1). La misma ley reconoce el derecho a la educación y la inclusión educativa (arts. 27 y 28).\n\nPara efectos de la ley, persona con discapacidad es quien, por una deficiencia física, mental, intelectual o sensorial, tiene restringida de forma permanente su capacidad para realizar actividades esenciales de la vida diaria, en la proporción que fija el reglamento (art. 6). Un diagnóstico de autismo no equivale automáticamente a una calificación de discapacidad: esta se obtiene mediante un trámite.\n\nLa calificación la realiza la autoridad sanitaria nacional; es voluntaria, personalizada y gratuita (art. 9). El Ministerio de Salud Pública la realiza en establecimientos de primer nivel y pide, entre otros requisitos, un informe médico o psicológico de profesionales habilitados (Ministerio de Salud Pública del Ecuador, 2026). Desde 2025, la cédula de identidad reemplaza al carné de discapacidad y registra el porcentaje de discapacidad (El Universo, 2024).",
         importance="Conocer los derechos ayuda a las familias a solicitar apoyos y a hacer trámites con información clara. También permite a los docentes comprender el marco que respalda las adaptaciones en el aula.",
         examples="Una familia quiere saber si su hijo puede obtener la calificación de discapacidad y qué documentos necesita.\nUn padre pregunta si el carné antiguo sigue siendo válido.\nUna docente busca el respaldo legal de la inclusión educativa para planificar adaptaciones.\nUna madre necesita orientación para su primer trámite en el centro de salud.",
         practice="Lee directamente las normas y los trámites oficiales citados, y consulta el directorio para encontrar organizaciones que orientan a las familias.",
         activities=[], materials=[], videos=[], action="legal",
         recommendations="Guarda copias de todos los informes médicos, psicológicos y educativos.\nAntes de un trámite, confirma los requisitos actualizados en la fuente oficial.\nPide orientación a asociaciones de familias con experiencia en estos procesos.",
         precautions="Esta cápsula es informativa y no es asesoría legal.\nLas normas y los trámites cambian: verifica siempre la vigencia en el Registro Oficial y en gob.ec.\nDesconfía de intermediarios que cobren por trámites gratuitos.",
         sources=["lod", "msp", "universo"], topics=["derechos"]),
    dict(key="ayuda", order=9, theme="ayuda", visual="ayuda",
         title="Cómo buscar orientación y ayuda profesional",
         description="Qué hacer si algo del desarrollo te preocupa y cómo llegar preparados a la consulta.",
         explanation="Si algo del desarrollo de tu hija o hijo te preocupa, no esperes. Si no alcanza los indicadores esperados para su edad, si pierde habilidades que ya tenía o si tienes otras preocupaciones, habla con su médico y pide una evaluación del desarrollo (CDC, 2026).\n\nEn Ecuador, un estudio con 767 familias encontró que la mayoría consultó a cuatro o más profesionales antes de obtener un diagnóstico, y que muchas vivieron el proceso con falta de información y de servicios (Buffle et al., 2024). Por eso conviene llegar a cada consulta con observaciones concretas y guardar copias de todas las evaluaciones (NIMH, 2025).\n\nEl camino suele empezar en el centro de salud o con el pediatra, que puede derivar a especialistas para una evaluación más completa. Las asociaciones de familias y algunos servicios públicos también ofrecen orientación.",
         importance="Una evaluación oportuna permite acceder antes a los apoyos. Mientras tanto, nada impide empezar en casa con estrategias sencillas, como los apoyos visuales.\n\nLlegar preparados a la consulta ahorra tiempo, evita repetir la historia en cada cita y ayuda al profesional a comprender mejor la situación.",
         examples="A los dos años, una niña dejó de decir palabras que antes usaba: es motivo para consultar pronto.\nUn padre lleva a la consulta una lista de ejemplos con fechas.\nUna docente nota dificultades y sugiere a la familia conversar con el DECE.\nUna familia busca en el directorio una asociación que la oriente sobre el proceso.",
         practice="Prepara la consulta con el registro de observaciones y busca en el directorio servicios y organizaciones con información verificada.",
         activities=[], materials=["registro", "ficha"], videos=["cdc"], action="directorio",
         recommendations="Anota lo que observas, con ejemplos y fechas.\nLleva tus preguntas escritas a la consulta.\nGuarda copias de informes y evaluaciones en una carpeta.\nPide que te expliquen los resultados con palabras sencillas.",
         precautions="Las listas de señales orientan, pero no reemplazan una evaluación profesional.\nVerifica que los profesionales estén habilitados para ejercer.\nDesconfía de quien ofrezca diagnósticos o tratamientos por redes sociales.",
         sources=["cdc", "buffle24", "nimh"], topics=["apoyo"]),
]

INSTITUTIONS = [
    dict(title="APADA del Ecuador", kind="asociacion", province="Todo el país", canton="Quito (sede) y red nacional",
         description="Asociación de padres y madres que se presenta como «padres que ayudan a padres en el camino del autismo». Su sitio web reúne información sobre autismo, servicios, recursos, eventos, preguntas frecuentes y una red de organizaciones de apoyo en distintas ciudades del país.",
         services="Información sobre autismo, recursos y preguntas frecuentes en su sitio web\nRed de apoyo: directorio de organizaciones de autismo en varias ciudades, incluida Guayaquil",
         website="https://apadadelecuador.org", cost="no_informado", basis="informacion_publica",
         evidence_url="https://apadadelecuador.org/red-de-apoyo/",
         note="Información tomada del sitio oficial de la asociación (página «Red de apoyo»)."),
    dict(title="Fundación Sendero Azul", kind="fundacion", province="Guayas", canton="Guayaquil",
         description="Fundación creada en 2018 por padres de hijos con autismo. Según un reportaje de diario Expreso, atiende a más de 300 beneficiarios entre niños, adolescentes y familias, sin costo.",
         services="Capacitaciones para familias, docentes, profesionales de la salud y empresas\nGrupos de apoyo y encuentros de familias\nPrograma semanal en línea «Una mirada al autismo», con profesionales invitados\n«Club Senderos»: actividad semanal para trabajar habilidades sociales\nIniciativa «Comunícate» sobre comunicación aumentativa",
         population="Niñas, niños y adolescentes con autismo y sus familias",
         social="https://www.instagram.com/fundacionsenderoazul/", cost="gratuito", basis="informacion_publica",
         evidence_url="https://www.expreso.ec/buenavida/autismo-voz-propia-fundacion-transforma-vidas-amor-245927.html",
         note="Datos de un reportaje de diario Expreso del 11 de junio de 2025; la fundación también figura en la red de apoyo de APADA del Ecuador. Según la fuente, para ser beneficiario se requiere un formulario y el diagnóstico. Confirmar la vigencia de los programas con la fundación."),
    dict(title="Dirección de Inclusión Social del Municipio de Guayaquil", kind="servicio_publico", province="Guayas", canton="Guayaquil",
         description="Según la Alcaldía de Guayaquil, su Dirección de Inclusión Social atiende de forma gratuita a 690 niñas y niños con autismo en centros municipales como el Centro Municipal de Apoyo Audición y Lenguaje y el Centro Municipal de Desarrollo de Habilidades Valientes.",
         services="Atenciones terapéuticas y terapias artísticas\nEstimulación cognitiva y desarrollo de habilidades sociales\nAutonomía, independencia y gestión emocional\nRefuerzo escolar y adaptaciones curriculares\nEscolaridad especializada",
         inclusion="Refuerzo escolar, adaptaciones curriculares y escolaridad especializada, según la fuente.",
         website="https://guayaquil.gob.ec", phone="181 (línea general del Municipio de Guayaquil)", cost="gratuito",
         basis="informacion_publica",
         evidence_url="https://guayaquil.gob.ec/ninos-autismo-reciben-atencion-parte-direccion-inclusion-social/",
         note="Información publicada por la Alcaldía de Guayaquil el 3 de abril de 2025. La fuente no indica direcciones ni requisitos; confirmarlos con el Municipio."),
    dict(title="Centro Integral de Terapias de la Prefectura del Guayas", kind="servicio_publico", province="Guayas",
         canton="Guayas (ubicación por confirmar)",
         description="Centro de la Prefectura del Guayas, parte de su programa «Guayas Integra», que brinda terapias gratuitas a personas con discapacidad. El ingreso requiere una evaluación y depende de los cupos disponibles.",
         services="Terapias gratuitas para personas con discapacidad, previa evaluación\nTransporte de usuarios, según la fuente",
         address="Prefectura del Guayas: Av. Juan Illingworth 108 y Av. Simón Bolívar",
         phone="+593 4 372 7600 / +593 4 251 1677 (Prefectura del Guayas)", email="info.secretaria@guayas.gob.ec",
         website="https://guayas.gob.ec", cost="gratuito", basis="informacion_publica",
         evidence_url="https://guayas.gob.ec/el-centro-integral-de-terapias-aumenta-a-660-el-numero-de-usuarios/",
         note="Información publicada por la Prefectura del Guayas el 17 de julio de 2023. Tiene más de dos años: confirmar su vigencia, ubicación y requisitos antes de acudir."),
    dict(title="Centro Psicoeducativo Integral Isaac", kind="terapeutico", province="Guayas", canton="Guayaquil",
         description="Centro de Guayaquil que brinda atención terapéutica y educativa a niñas, niños y jóvenes con autismo. Un trabajo de titulación de la ESPOL lo describe como una de las primeras organizaciones de la ciudad en atender el autismo.",
         services="Atención terapéutica para personas con autismo\nAtención educativa (psicoeducativa)",
         population="Niñas, niños y jóvenes con autismo y sus familias",
         address="Sector La Alborada, Guayaquil (según prensa; confirmar la dirección actual)",
         website="https://www.centroisaac.com", cost="no_informado", basis="informacion_publica",
         evidence_url="https://www.centroisaac.com/centro-autismo-guayaquil",
         note="Información del sitio oficial del centro y de fuentes públicas (diario El Universo; trabajos de titulación de la ESPOL). Confirmar dirección, servicios, horarios y costos directamente con el centro."),
    dict(title="Calificación de discapacidad: Ministerio de Salud Pública", kind="tramite", province="Todo el país",
         canton="Establecimientos de salud de primer nivel del MSP",
         description="Trámite oficial y gratuito para obtener el certificado de calificación o recalificación de discapacidad. Requiere solicitud firmada, cédula o pasaporte y un informe médico o psicológico de profesionales habilitados que trabajen en la Red Pública Integral de Salud o en la Red Privada Complementaria.",
         services="Emisión gratuita del certificado de calificación o recalificación de discapacidad\nAtención presencial de 08:00 a 16:30 en establecimientos de primer nivel con equipos calificadores\nPara personas con discapacidad auditiva: agendamiento por videollamada en lengua de señas, línea 171, opción 4",
         website="https://www.gob.ec/msp/tramites/emision-certificado-calificacion-recalificacion-discapacidad-establecimiento-salud",
         cost="gratuito", basis="informacion_publica",
         evidence_url="https://www.gob.ec/msp/tramites/emision-certificado-calificacion-recalificacion-discapacidad-establecimiento-salud",
         note="Ficha oficial del trámite en gob.ec, actualizada el 15 de enero de 2026."),
]

FAQS = [
    ("¿Este sitio puede decirme si mi hija o hijo es autista?",
     "No. La información es educativa y orientativa. Solo un equipo profesional puede realizar una evaluación. Si algo te preocupa, consulta la cápsula sobre cómo buscar orientación y lleva tus observaciones a la consulta.",
     "Cómo buscar orientación", "capsule:ayuda"),
    ("¿Quién revisa la información?",
     "El equipo del proyecto redacta las cápsulas a partir de fuentes oficiales y científicas que realmente consultó, y cada una indica su fecha de revisión. Los aportes de la comunidad se revisan antes de publicarse. Las cápsulas indican si ya fueron revisadas por un profesional.",
     "Ver todas las fuentes", "/fuentes/"),
    ("¿Necesito una cuenta?",
     "No para leer, usar las actividades, imprimir materiales o crear agendas visuales. La cuenta sirve para guardar favoritos, comentar, compartir materiales y participar en el intercambio.",
     "", ""),
    ("¿Las instituciones del directorio están acreditadas?",
     "No necesariamente. Cada ficha indica la base de su verificación: acreditación, autorización, registro, información pública o descripción de la propia institución. Aparecer en el directorio no es una recomendación clínica.",
     "Ir al directorio", "/orientacion/directorio/"),
    ("¿Puedo imprimir y compartir los materiales?",
     "Sí, para uso personal y educativo. Los pictogramas son de Twemoji, con licencia CC BY 4.0: conserva el crédito cuando los compartas.",
     "Créditos y licencias", "/creditos/"),
    ("¿Cómo se obtiene la calificación de discapacidad?",
     "La realiza el Ministerio de Salud Pública de forma gratuita en establecimientos de primer nivel. Se necesita, entre otros requisitos, un informe médico o psicológico de profesionales habilitados. Confirma los requisitos actualizados en la ficha oficial del trámite.",
     "Ficha oficial del trámite", "https://www.gob.ec/msp/tramites/emision-certificado-calificacion-recalificacion-discapacidad-establecimiento-salud"),
]

INTERVIEW_QUESTIONS = [
    ("necesidades", "¿Cuáles son las dudas más frecuentes de las familias cuando reciben un diagnóstico de autismo?"),
    ("necesidades", "¿Qué necesidades de las familias del Guayas siguen sin respuesta?"),
    ("recursos", "¿Qué recursos educativos han visto que funcionan mejor en casa?"),
    ("recursos", "¿Qué recomiendan a las familias que quieren empezar a usar apoyos visuales?"),
    ("inclusion", "¿Qué pueden hacer las escuelas para recibir mejor a estudiantes autistas?"),
    ("inclusion", "¿Cómo puede mejorar la comunicación entre la familia y la escuela?"),
    ("orientacion", "¿Dónde puede buscar orientación una familia que no sabe por dónde empezar?"),
    ("orientacion", "¿Qué servicios ofrece su organización y cómo se accede a ellos?"),
    ("cotidiano", "¿Qué situaciones cotidianas resultan más difíciles para las familias y cómo las acompañan?"),
    ("cotidiano", "¿Qué mensaje le darían a una familia que se siente sola en este camino?"),
]


class Command(BaseCommand):
    help = "Carga el contenido inicial verificado (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--usuarios-demo", action="store_true",
                            help="Crea cuentas de prueba (solo con DJANGO_DEBUG=True).")

    def publish(self, obj):
        if obj.status != Status.APPROVED:
            obj.status = Status.APPROVED
            obj.reviewed_at = timezone.now()
            obj.save(update_fields=["status", "reviewed_at"])
            record(obj, None, ModerationAction.Action.APPROVE, "", Status.APPROVED, "Contenido inicial del proyecto")

    @transaction.atomic
    def handle(self, *args, **opts):
        call_command("configurar_roles", verbosity=0)
        cfg = SiteConfig.load()
        if not cfg.contact_email:
            cfg.contact_email = settings.SITE_CONTACT_EMAIL
            cfg.save()

        topics = {}
        for i, (slug, name, picto, desc) in enumerate(TOPICS):
            t, _ = Topic.objects.update_or_create(slug=slug, defaults={"name": name, "pictogram": picto, "description": desc,
                                                                      "order": i})
            topics[slug] = t

        sources = {}
        for key, d in SOURCES.items():
            s, _ = Source.objects.update_or_create(short=d["short"], defaults={
                "citation": d["citation"], "url": d["url"], "kind": d["kind"], "accessed_on": TODAY, "notes": d["notes"]})
            s.topics.set([topics[t] for t in d["topics"]])
            sources[key] = s

        pics = {}
        for cat, items in PICTOGRAMS:
            for i, (code, label) in enumerate(items):
                p, _ = Pictogram.objects.update_or_create(code=code, defaults={"label": label, "category": cat, "order": i})
                pics[label] = p

        materials = {}
        for key, d in MATERIALS.items():
            m, created = Material.objects.get_or_create(title=d["title"], defaults={
                "kind": d["kind"], "layout": d["layout"], "description": d["description"], "how_to_use": d["how"],
                "worksheet_prompts": d.get("prompts", ""), "origin": Origin.EDITORIAL, "featured": d.get("featured", False),
                "credit": "Equipo del proyecto. Pictogramas: Twemoji, © Twitter, Inc. y otros colaboradores",
                "license": "Uso educativo libre. Pictogramas: CC BY 4.0"})
            if created:
                for i, item in enumerate(d.get("items", [])):
                    label, custom = (item, "") if isinstance(item, str) else (item[0], item[1] or "")
                    MaterialItem.objects.create(material=m, pictogram=pics[label], label=custom, order=i)
            m.topics.set([topics[t] for t in d["topics"]])
            self.publish(m)
            materials[key] = m

        activities = {}
        for key, d in ACTIVITIES.items():
            a, _ = Activity.objects.get_or_create(title=d["title"], defaults={
                "kind": d["kind"], "age_range": d["age"], "duration": d["duration"], "place": d["place"],
                "description": d["description"], "objective": d["objective"], "materials_needed": d["materials"],
                "instructions": d["steps"], "adaptations": d["adaptations"], "precautions": d["precautions"],
                "origin": Origin.EDITORIAL, "featured": d.get("featured", False)})
            a.related_materials.set([materials[m] for m in d["materials_rel"]])
            a.topics.set([topics[t] for t in d["topics"]])
            a.sources.set([sources[s] for s in d["sources"]])
            self.publish(a)
            activities[key] = a

        cdc_video, _ = Video.objects.get_or_create(title="Videos «Aprenda los signos. Reaccione pronto.»", defaults={
            "description": "Videos oficiales en español sobre los indicadores del desarrollo infantil y qué hacer si existe una preocupación.",
            "publisher": "Centros para el Control y la Prevención de Enfermedades (CDC)",
            "url": "https://cdc.gov/act-early/es/resources/videos.html", "language": "Español",
            "why_recommended": "Son materiales oficiales en español. Explican por qué conviene conocer los indicadores del desarrollo y qué hacer ante una preocupación, e incluyen experiencias de familias. La página ofrece la transcripción de un video. Está pensada para Estados Unidos: los servicios que menciona no corresponden a Ecuador.",
            "audience": "familias", "reviewed_on": TODAY, "origin": Origin.INSTITUTIONAL})
        cdc_video.topics.set([topics["apoyo"]])
        self.publish(cdc_video)
        videos = {"cdc": cdc_video}

        capsules = {}
        for d in CAPSULES:
            c, _ = Capsule.objects.get_or_create(title=d["title"], defaults={
                "theme": d["theme"], "order": d["order"], "description": d["description"], "explanation": d["explanation"],
                "importance": d["importance"], "examples": d["examples"], "practice_intro": d["practice"],
                "action": d["action"], "visual": d["visual"], "recommendations": d["recommendations"],
                "precautions": d["precautions"], "revised_on": TODAY, "origin": Origin.EDITORIAL,
                "featured": d.get("featured", False)})
            c.related_activities.set([activities[a] for a in d["activities"]])
            c.related_materials.set([materials[m] for m in d["materials"]])
            c.related_videos.set([videos[v] for v in d["videos"]])
            c.sources.set([sources[s] for s in d["sources"]])
            c.topics.set([topics[t] for t in d["topics"]])
            self.publish(c)
            capsules[d["key"]] = c

        for d in INSTITUTIONS:
            inst, _ = Institution.objects.get_or_create(title=d["title"], defaults={
                "kind": d["kind"], "province": d["province"], "canton": d["canton"], "description": d["description"],
                "services": d["services"], "inclusion_services": d.get("inclusion", ""), "population": d.get("population", ""),
                "address": d.get("address", ""), "phone": d.get("phone", ""), "email": d.get("email", ""),
                "website": d.get("website", ""), "social": d.get("social", ""), "cost": d["cost"],
                "verification_basis": d["basis"], "evidence_url": d["evidence_url"], "evidence_note": d["note"],
                "last_reviewed": TODAY, "origin": Origin.INSTITUTIONAL})
            inst.topics.set([topics["apoyo"]])
            self.publish(inst)

        for i, (q, a, label, link) in enumerate(FAQS):
            if link.startswith("capsule:"):
                link = capsules[link.split(":")[1]].get_absolute_url()
            FAQ.objects.update_or_create(question=q, defaults={"answer": a, "link_label": label, "link_url": link, "order": i})

        iv, created = Interview.objects.get_or_create(title="Entrevista con la organización colaboradora", defaults={
            "description": "Conversaremos con la organización colaboradora del proyecto sobre las necesidades de las familias, los recursos educativos, la inclusión y la orientación. La organización, la persona entrevistada y la fecha se confirmarán antes de publicar.",
            "status": Status.DRAFT, "show_as_upcoming": True, "origin": Origin.INSTITUTIONAL})
        if created:
            for i, (theme, q) in enumerate(INTERVIEW_QUESTIONS):
                InterviewQuestion.objects.create(interview=iv, theme=theme, question=q, order=i)
        iv.topics.set([topics["apoyo"], topics["escuela"]])

        if opts["usuarios_demo"]:
            if not settings.DEBUG:
                raise CommandError("Las cuentas de prueba solo se crean con DJANGO_DEBUG=True.")
            User = get_user_model()
            for email, pwd, name, part in [("familia.demo@ejemplo.org", "Demo-familia-2026", "Familia de prueba", "familia"),
                                           ("docente.demo@ejemplo.org", "Demo-docente-2026", "Docente de prueba", "docente")]:
                u, created = User.objects.get_or_create(email=email, defaults={"first_name": name})
                if created:
                    u.set_password(pwd)
                    u.save()
                    u.profile.participation = part
                    u.profile.display_name = name
                    u.profile.save()
            self.stdout.write("Cuentas de prueba: familia.demo@ejemplo.org / Demo-familia-2026 · "
                              "docente.demo@ejemplo.org / Demo-docente-2026")

        self.stdout.write(self.style.SUCCESS(
            f"Contenido cargado: {Capsule.objects.public().count()} cápsulas, {Activity.objects.public().count()} actividades, "
            f"{Material.objects.public().count()} materiales, {Pictogram.objects.count()} pictogramas, "
            f"{Institution.objects.public().count()} instituciones, {Source.objects.count()} fuentes."))

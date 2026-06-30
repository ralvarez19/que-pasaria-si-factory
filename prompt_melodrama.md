Actúa como guionista de videos virales de drama emocional cotidiano, con escenas visualmente exageradas y muy expresivas.

Necesito una sola historia larga dividida en varias partes, en formato JSON válido para una fábrica automática de videos con IA.

Los videos serán procesados automáticamente, así que cada parte debe ser un JSON completo, correcto y listo para guardar como archivo `.json`.

## Objetivo

Crear una historia emocional, cotidiana y viral, donde una persona común enfrenta una situación injusta causada por gente abusiva, egoísta o manipuladora.

La historia debe provocar:

- tristeza;
- indignación;
- empatía;
- tensión;
- esperanza;
- ganas de ver la siguiente parte.

Debe sentirse como una mezcla entre:

- melodrama de novela;
- intensidad visual tipo anime;
- emociones exageradas;
- reacciones muy expresivas;
- escenas impactantes y virales.

No importa si la emoción está exagerada, siempre que siga siendo entendible y poderosa.

## Importante

Quiero la MISMA historia dividida en partes.
No quiero historias diferentes.
Cada parte debe continuar exactamente desde la anterior.
Los personajes principales deben mantenerse iguales.
Cada parte debe terminar con un cliffhanger emocional.
Solo la última parte puede cerrar el arco principal.

## Tema de la historia

Una madre humilde es humillada por una mujer rica en un lugar público, pero poco a poco se descubre que la madre esconde una verdad que cambiará todo.

## Cantidad de partes

Genera 5 partes de la misma historia.

## Configuración fija de cada parte

Cada JSON debe tener:

{
  "duration_seconds": 120,
  "scene_duration_seconds": 6,
  "language": "es",
  "aspect_ratio": "16:9",
  "width": 1280,
  "height": 720,
  "fps": 25,
  "style": "hyper emotional melodrama viral, telenovela anime hybrid"
}

Cada parte debe tener exactamente 20 escenas de 6 segundos.

## Formato obligatorio

Cada JSON debe incluir obligatoriamente estos campos:

- topic
- title
- duration_seconds
- scene_duration_seconds
- language
- aspect_ratio
- width
- height
- fps
- style
- scenes

## Cada escena debe tener

- scene_number
- duration_seconds
- visual_prompt
- narration
- subtitle
- tts_text

## Reglas para narration

Cada narration debe:

- sonar dramática, intensa y emocional;
- conectar claramente con la escena anterior;
- durar aproximadamente 4 a 5 segundos al leerse;
- tener mínimo 75 caracteres;
- tener máximo 135 caracteres;
- tener mínimo 12 palabras;
- tener máximo 20 palabras;
- sentirse como parte de una historia continua;
- no usar puntos suspensivos;
- no usar la frase “Cada consecuencia abre la puerta a la siguiente”.

## Reglas para subtitle

subtitle debe ser exactamente igual a narration.

## Reglas para tts_text

tts_text debe conservar el mismo significado de narration, pero limpio para TTS:

- sin puntos;
- sin puntos suspensivos;
- reemplazar puntos por comas;
- mantener tildes y ñ;
- no cortar palabras.

## Reglas para visual_prompt

Cada visual_prompt debe estar en inglés.

Debe mostrar escenas mucho más animadas, exageradas y emocionales.

Cada visual_prompt debe incluir elementos como:

- hyper emotional melodrama
- expressive faces
- dramatic body language
- intense emotional reaction
- cinematic close-up
- dramatic atmosphere
- smooth camera movement
- highly detailed

Puede tener mezcla visual de novela dramática y anime emocional.

Debe mostrar:

- lágrimas visibles;
- miradas intensas;
- sorpresa exagerada;
- vergüenza;
- rabia contenida;
- arrogancia marcada;
- tensión social;
- reacciones del entorno.

No debe incluir texto en pantalla.
No debe incluir logos.
No debe incluir marcas.
No debe incluir celebridades.
No debe mostrar gore ni violencia gráfica.

## Consistencia de personajes

Mantén los mismos personajes en todas las partes:

- Elena, una madre humilde de 38 años, cabello oscuro recogido, ropa sencilla, mirada cansada pero digna
- Sofía, su hija de 10 años, tímida, sensible, con uniforme escolar sencillo
- Verónica, una mujer rica y arrogante de 45 años, ropa elegante, expresión fría, postura dominante
- Andrés, gerente del lugar, nervioso, preocupado por complacer a la gente rica

## Tono visual

Quiero escenas más vivas y con emociones exageradas.

Ejemplos visuales deseados:
- primerísimos planos de lágrimas;
- manos temblando;
- mirada cruel de la antagonista;
- niña conteniendo el llanto;
- gente observando sorprendida;
- giros de cabeza dramáticos;
- cámara acercándose lentamente al rostro;
- tensión emocional fuerte en cada escena.

## Estructura general de la historia

Parte 1:
Presenta la humillación pública y el dolor de la madre.

Parte 2:
La situación empeora y la mujer rica manipula a todos.

Parte 3:
Aparecen pistas de que la madre guarda una verdad importante.

Parte 4:
La verdad comienza a salir y cambia la percepción de todos.

Parte 5:
La verdad se revela por completo y la madre recupera su dignidad.

## Salida requerida

Dame las 5 partes completas.

Para cada parte entrega:

1. nombre sugerido del archivo
2. JSON completo válido listo para copiar y guardar

Antes de responder, revisa internamente:

- que cada JSON tenga exactamente 20 escenas;
- que cada escena tenga duration_seconds: 6;
- que narration cumpla el rango de longitud;
- que subtitle sea igual a narration;
- que tts_text no tenga puntos;
- que visual_prompt esté en inglés;
- que los personajes sean consistentes;
- que todas las partes formen una sola historia continua.

No agregues comentarios dentro del JSON.
No uses markdown dentro del JSON.
No entregues explicaciones largas.
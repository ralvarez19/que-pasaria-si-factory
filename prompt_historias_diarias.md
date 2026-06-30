Actúa como guionista de videos virales de drama emocional cotidiano.

Necesito una sola historia larga dividida en varias partes, en formato JSON válido para una fábrica automática de videos con IA.

Los videos serán procesados automáticamente, así que cada parte debe ser un JSON completo, correcto y listo para guardar como archivo `.json`.

## Objetivo

Crear una historia emocional, cotidiana y viral, donde una persona común enfrenta una situación injusta causada por gente abusiva, egoísta o manipuladora.

La historia debe provocar:

* tristeza;
* indignación;
* empatía;
* tensión;
* esperanza;
* deseo de ver la siguiente parte.

Debe sentirse como una historia real que podría pasar en la vida diaria.

## Tema de la historia

Crea una historia sobre:

Una madre humilde es humillada por una mujer rica en un lugar público, pero poco a poco se descubre que la madre esconde una verdad que cambiará todo.

## Importante

No quiero historias diferentes.

Quiero la MISMA historia dividida en partes.

Cada parte debe continuar exactamente desde la anterior.

Los personajes principales deben mantenerse iguales en todas las partes.

El conflicto debe avanzar poco a poco.

No cierres la historia en la parte 1.

No cierres la historia en la parte 2.

No cierres la historia en la parte 3.

Cada parte debe terminar con un cliffhanger emocional.

Solo la última parte puede cerrar el arco principal.

## Cantidad de partes

Genera 5 partes de la misma historia.

Cada parte debe ser un JSON independiente.

Los archivos sugeridos deben llamarse así:

* 01_madre_humillada_parte_01.json
* 02_madre_humillada_parte_02.json
* 03_madre_humillada_parte_03.json
* 04_madre_humillada_parte_04.json
* 05_madre_humillada_parte_05.json

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
"style": "realistic emotional drama viral"
}

Cada parte debe tener exactamente 20 escenas de 6 segundos.

La cantidad de escenas debe coincidir con esta fórmula:

120 / 6 = 20 escenas

## Formato obligatorio

Cada JSON debe incluir obligatoriamente estos campos:

* topic
* title
* duration_seconds
* scene_duration_seconds
* language
* aspect_ratio
* width
* height
* fps
* style
* scenes

No omitas ningún campo.

No agregues campos extra si no son necesarios.

## Cada escena debe tener

* scene_number
* duration_seconds
* visual_prompt
* narration
* subtitle
* tts_text

Cada escena debe tener:

"duration_seconds": 6

## Reglas para narration

Cada narration debe:

* sonar como narración dramática, emocional y viral;
* conectar claramente con la escena anterior;
* durar aproximadamente 4 a 5 segundos al leerse;
* tener mínimo 75 caracteres;
* tener máximo 135 caracteres;
* tener mínimo 12 palabras;
* tener máximo 20 palabras;
* no ser una frase demasiado corta;
* no ser una frase demasiado larga;
* no usar puntos suspensivos;
* evitar puntos si no son necesarios;
* usar comas con naturalidad;
* no repetir estructuras en todas las escenas;
* no usar frases genéricas como “nada volvería a ser igual” en exceso;
* no usar “Cada consecuencia abre la puerta a la siguiente”.

Las narraciones deben sentirse como una historia continua, no como frases aisladas.

## Reglas para subtitle

El campo subtitle debe ser exactamente igual a narration.

## Reglas para tts_text

El campo tts_text debe ser una versión limpia de narration para voz IA.

Reglas:

* debe conservar el mismo significado;
* no usar puntos;
* no usar puntos suspensivos;
* reemplazar puntos por comas;
* mantener tildes y ñ;
* mantener signos ¿ ? si es pregunta;
* no cortar palabras;
* debe tener mínimo 75 caracteres;
* debe tener mínimo 12 palabras;
* debe sonar natural al leerse.

## Reglas para visual_prompt

Cada visual_prompt debe estar en inglés.

Debe describir claramente:

* personajes consistentes;
* ambiente cotidiano y realista;
* emoción visible en rostros y lenguaje corporal;
* tensión social o emocional;
* iluminación cinematográfica;
* movimiento suave de cámara;
* estilo realista dramático.

Debe incluir frases como:

* realistic emotional drama
* cinematic scene
* natural lighting
* expressive faces
* smooth camera movement
* dramatic atmosphere
* highly detailed

No debe incluir texto en pantalla.
No debe incluir logos.
No debe incluir marcas.
No debe incluir celebridades.
No debe mostrar violencia gráfica.

## Consistencia de personajes

Define personajes principales y repítelos en todos los visual_prompt de todas las partes.

Personajes sugeridos:

* Elena, una madre humilde de 38 años, cabello oscuro recogido, ropa sencilla, mirada cansada pero digna
* Sofía, su hija de 10 años, tímida, sensible, con uniforme escolar sencillo
* Verónica, una mujer rica y arrogante de 45 años, ropa elegante, expresión fría, postura dominante
* Andrés, gerente del lugar, nervioso, preocupado por complacer a la gente rica

Puedes agregar personajes secundarios, pero no cambies los principales.

## Estructura narrativa general de las 5 partes

Parte 1:
Presenta la injusticia principal, la humillación pública y el dolor de la madre.

Parte 2:
La situación empeora, la mujer rica manipula a todos y la madre parece quedarse sola.

Parte 3:
Aparecen pistas de que la madre oculta una verdad importante sobre su pasado.

Parte 4:
La verdad empieza a salir, algunos personajes cambian de bando y la abusiva pierde control.

Parte 5:
Se revela la verdad completa, la madre recupera su dignidad y se cierra el conflicto principal.

## Estructura de cada parte

Cada parte debe tener 20 escenas.

Usa esta estructura interna:

1. Hook emocional fuerte.
2. Continuación directa de la escena anterior o del cliffhanger anterior.
3. Reacción de la víctima.
4. Reacción del abusivo.
5. La tensión social aumenta.
6. Alguien presencia la injusticia.
7. La víctima intenta mantener la calma.
8. El abusivo manipula la situación.
9. Se revela un detalle importante.
10. El entorno empieza a incomodarse.
11. La víctima casi se rinde.
12. Aparece un gesto de empatía.
13. La injusticia se vuelve más evidente.
14. La víctima encuentra fuerza.
15. Alguien empieza a dudar del abusivo.
16. Aparece una pista o prueba.
17. El abusivo intenta ocultar algo.
18. La víctima recupera un poco de dignidad.
19. Giro emocional fuerte.
20. Cliffhanger que obliga a ver la siguiente parte.

En la última parte, la escena 20 sí puede cerrar con una frase emocional fuerte, pero debe dejar espacio para una posible nueva historia.

## Salida requerida

Dame las 5 partes completas.

Para cada parte entrega:

1. Nombre sugerido del archivo.
2. JSON completo válido listo para copiar y guardar.

Antes de responder, revisa internamente cada JSON:

* que tenga topic;
* que tenga title;
* que tenga duration_seconds: 120;
* que tenga scene_duration_seconds: 6;
* que tenga exactamente 20 escenas;
* que cada escena tenga duration_seconds: 6;
* que cada narration tenga mínimo 75 caracteres;
* que cada narration tenga mínimo 12 palabras;
* que cada narration tenga máximo 135 caracteres;
* que cada narration tenga máximo 20 palabras;
* que subtitle sea igual a narration;
* que tts_text no tenga puntos;
* que visual_prompt esté en inglés;
* que los personajes sean consistentes en todas las partes;
* que cada parte continúe la misma historia, no historias diferentes.

No agregues comentarios dentro del JSON.
No uses markdown dentro del JSON.
No entregues explicaciones largas.

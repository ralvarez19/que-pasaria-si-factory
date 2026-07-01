Actúa como guionista de videos virales de drama sobrenatural cotidiano, estilo “sistema de poder”, injusticia, venganza emocional y superación.

Necesito una sola historia larga dividida en varias partes, en formato JSON válido para una fábrica automática de videos con IA.

Los videos serán procesados automáticamente, así que cada parte debe ser un JSON completo, correcto y listo para guardar como archivo `.json`.

## Objetivo

Crear una historia emocional y viral donde un protagonista común sufre una injusticia fuerte causada por personas abusivas, manipuladoras o crueles.

Después de tocar fondo, aparece un sistema misterioso que lo recompensa con un poder especial.

Ese poder debe ayudarlo a enfrentar a quienes lo humillaron, exponer sus mentiras y recuperar su dignidad.

La historia debe provocar:

* tristeza;
* indignación;
* rabia emocional;
* empatía;
* tensión;
* satisfacción;
* esperanza;
* ganas de ver la siguiente parte.

Debe sentirse como una mezcla entre:

* drama cotidiano;
* novela intensa;
* anime de sistema;
* power fantasy;
* venganza emocional;
* justicia sobrenatural.

## Importante sobre la venganza

La venganza no debe ser violencia gráfica.

No uses gore.
No uses tortura.
No uses escenas explícitas de daño físico.
No glorifiques asesinatos ni crueldad extrema.

La venganza debe sentirse poderosa, pero basada en:

* revelar verdades ocultas;
* exponer mentiras;
* hacer que los abusivos pierdan su máscara;
* devolverle al protagonista su dignidad;
* castigar emocional o socialmente a los culpables;
* hacer que los enemigos caigan por sus propias acciones.

## Tipo de sistema

Incluye un sistema sobrenatural o misterioso que solo el protagonista puede ver.

Ejemplos:

* Sistema de Justicia Activado
* Sistema de Recompensa por Sufrimiento
* Sistema del Destino
* Sistema de Karma
* Sistema del Testigo Invisible
* Sistema de la Verdad

El sistema debe aparecer con mensajes visuales tipo interfaz, pero en visual_prompt no pongas texto en pantalla. Describe el efecto visual sin pedir letras.

Ejemplo narrativo:

“El sistema apareció frente a él, como una luz imposible que nadie más podía ver”

## Poderes recomendados

Elige un poder principal que sirva para la historia.

Ejemplos:

* detectar mentiras;
* ver recuerdos ocultos;
* escuchar la verdad detrás de las palabras;
* revelar pruebas invisibles;
* detener el tiempo por unos segundos;
* copiar habilidades;
* hacer que las mentiras se manifiesten físicamente;
* ver el karma de cada persona;
* obligar a los culpables a enfrentar sus propios recuerdos;
* transformar el dolor sufrido en fuerza sobrenatural.

El poder debe tener reglas y límites.
No debe resolver todo de inmediato.
Debe crecer poco a poco en cada parte.

## Tema de la historia

Crea una historia sobre:

Un joven trabajador humilde es humillado, traicionado y acusado injustamente por sus compañeros y su jefe, pero cuando está a punto de perderlo todo, un sistema misterioso lo recompensa con un poder que le permitirá revelar la verdad y vengarse de quienes destruyeron su vida.

## Importante

No quiero historias diferentes.

Quiero la MISMA historia dividida en partes.

Cada parte debe continuar exactamente desde la anterior.

Los personajes principales deben mantenerse iguales en todas las partes.

El conflicto debe avanzar poco a poco.

No cierres la historia en la parte 1.
No cierres la historia en la parte 2.
No cierres la historia en la parte 3.
No cierres la historia en la parte 4.

Cada parte debe terminar con un cliffhanger emocional.

Solo la última parte puede cerrar el arco principal.

## Cantidad de partes

Genera 5 partes de la misma historia.

Cada parte debe ser un JSON independiente.

Los archivos sugeridos deben llamarse así:

* 01_sistema_del_karma_parte_01.json
* 02_sistema_del_karma_parte_02.json
* 03_sistema_del_karma_parte_03.json
* 04_sistema_del_karma_parte_04.json
* 05_sistema_del_karma_parte_05.json

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
"style": "emotional supernatural revenge drama viral, system power fantasy"
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

* sonar intensa, emocional y viral;
* conectar claramente con la escena anterior;
* durar aproximadamente 4 a 5 segundos al leerse;
* tener mínimo 75 caracteres;
* tener máximo 135 caracteres;
* tener mínimo 12 palabras;
* tener máximo 20 palabras;
* sentirse como parte de una historia continua;
* no usar puntos suspensivos;
* evitar puntos si no son necesarios;
* usar comas con naturalidad;
* no repetir estructuras en todas las escenas;
* no usar frases genéricas como “nada volvería a ser igual” en exceso;
* no usar “Cada consecuencia abre la puerta a la siguiente”.

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

Debe describir escenas muy emocionales, dramáticas y visualmente potentes.

Cada visual_prompt debe incluir elementos como:

* emotional supernatural revenge drama
* cinematic scene
* expressive faces
* dramatic body language
* intense emotional reaction
* glowing mysterious system interface effect
* dramatic lighting
* smooth camera movement
* highly detailed

Puede mezclar realismo cotidiano con energía visual tipo anime o novela dramática.

Debe mostrar:

* humillación pública;
* miradas crueles;
* lágrimas contenidas;
* rabia silenciosa;
* manos temblando;
* sistema sobrenatural brillando;
* enemigos sorprendidos;
* pruebas revelándose;
* protagonista recuperando poder y dignidad.

No debe incluir texto en pantalla.
No debe incluir logos.
No debe incluir marcas.
No debe incluir celebridades.
No debe mostrar gore ni violencia gráfica.

## Consistencia de personajes

Mantén los mismos personajes en todas las partes:

* Mateo, joven trabajador humilde de 24 años, cabello negro despeinado, ropa sencilla, mirada cansada pero determinada
* Clara, amiga honesta de Mateo, 23 años, mirada sensible, ropa casual, actitud protectora
* Ramiro, jefe abusivo de 45 años, traje elegante, expresión arrogante, postura dominante
* Darío, compañero traicionero de 28 años, sonrisa falsa, actitud manipuladora
* El Sistema, presencia visual misteriosa que solo Mateo puede percibir, luz azul o dorada flotando alrededor de él

Puedes agregar personajes secundarios, pero no cambies los principales.

## Estructura general de las 5 partes

Parte 1:
Mateo es humillado, traicionado y acusado injustamente, hasta que el sistema aparece cuando toca fondo.

Parte 2:
Mateo descubre su primer poder, pero todavía no sabe controlarlo y sus enemigos siguen atacándolo.

Parte 3:
Mateo empieza a revelar mentiras pequeñas, mientras descubre que la traición viene de alguien cercano.

Parte 4:
El sistema evoluciona, las pruebas ocultas salen a la luz y los enemigos empiezan a perder control.

Parte 5:
Mateo enfrenta a todos, revela la verdad completa y logra una venganza emocional sin violencia gráfica.

## Estructura interna de cada parte

Cada parte debe tener 20 escenas.

Usa esta estructura:

1. Hook emocional fuerte.
2. Continuación directa de la escena anterior o del cliffhanger anterior.
3. Mateo enfrenta una injusticia o consecuencia.
4. Ramiro o Darío manipulan la situación.
5. Clara intenta ayudar o duda de lo que ve.
6. Mateo toca fondo emocionalmente.
7. Aparece o reacciona el sistema.
8. El poder se manifiesta de forma pequeña.
9. Los enemigos se burlan o se confían.
10. Mateo descubre una regla del poder.
11. La tensión aumenta en público.
12. El sistema revela una pista.
13. Mateo decide actuar.
14. Un enemigo queda expuesto parcialmente.
15. La gente empieza a dudar de la versión falsa.
16. Ramiro o Darío intentan ocultar la verdad.
17. El poder evoluciona o muestra un límite.
18. Mateo recupera algo de dignidad.
19. Giro emocional fuerte.
20. Cliffhanger que obliga a ver la siguiente parte.

En la última parte, la escena 20 puede cerrar el arco principal con una frase poderosa.

## Final obligatorio

Cada parte excepto la última debe terminar con un cliffhanger.

Ejemplos:

* “Entonces el sistema mostró el nombre del verdadero culpable, y Mateo dejó de respirar”
* “Pero cuando Mateo tocó la prueba, vio un recuerdo que jamás debió existir”
* “Ramiro sonrió frente a todos, sin saber que el sistema ya había marcado su mentira”
* “Y justo cuando Mateo iba a hablar, Clara apareció con una grabación imposible”

## Salida requerida

Dame las 5 partes completas.

Para cada parte entrega:

1. nombre sugerido del archivo
2. JSON completo válido listo para copiar y guardar

Antes de responder, revisa internamente:

* que cada JSON tenga exactamente 20 escenas;
* que cada escena tenga duration_seconds: 6;
* que narration cumpla el rango de longitud;
* que subtitle sea igual a narration;
* que tts_text no tenga puntos;
* que visual_prompt esté en inglés;
* que los personajes sean consistentes;
* que todas las partes formen una sola historia continua;
* que la venganza sea emocional, social o sobrenatural, no violencia gráfica.

No agregues comentarios dentro del JSON.
No uses markdown dentro del JSON.
No entregues explicaciones largas.

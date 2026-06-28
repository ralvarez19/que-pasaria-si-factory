Actúa como guionista de videos documentales cortos para una serie llamada “¿Qué pasaría si…?”.

Necesito guiones en formato JSON válido para una fábrica automática de videos con IA.

Cada JSON debe tener exactamente 15 escenas de 4 segundos, duración total 60 segundos.

Configuración fija:
duration_seconds: 60
scene_duration_seconds: 4
language: es
aspect_ratio: 16:9
width: 1280
height: 720
fps: 25

Cada escena debe tener:
- scene_number
- duration_seconds
- visual_prompt
- narration
- subtitle
- tts_text

Reglas estrictas para narration:
- debe sonar como documental;
- debe conectar con la escena anterior;
- debe tener entre 60 y 115 caracteres;
- idealmente entre 70 y 110 caracteres;
- debe tener entre 10 y 16 palabras;
- no debe ser una frase demasiado corta;
- no debe ser una frase demasiado larga;
- no usar “Cada consecuencia abre la puerta a la siguiente”;
- no repetir estructuras;
- subtitle debe ser exactamente igual a narration.

Reglas para tts_text:
- debe conservar el mismo significado de narration;
- no debe tener puntos;
- reemplaza puntos por comas;
- no uses puntos suspensivos;
- mantiene tildes y ñ;
- mantiene signos ¿ ? si es pregunta;
- debe sonar natural al leerse.

visual_prompt:
- debe estar en inglés;
- estilo cinematic documentary;
- realistic lighting;
- smooth camera movement;
- dramatic atmosphere;
- highly detailed;
- no text, no logos, no brands.

Antes de entregarme el JSON, revisa internamente cada narration:
- si tiene menos de 60 caracteres, alárgala;
- si tiene más de 115 caracteres, acórtala;
- si tiene menos de 10 palabras, alárgala;
- si tiene más de 16 palabras, acórtala;
- verifica que subtitle sea igual a narration;
- verifica que tts_text no tenga puntos.

Dame 3 historias completas.

Para cada historia entrega:
1. nombre sugerido del archivo, por ejemplo 01_sol_se_apaga.json
2. JSON completo válido listo para copiar

No agregues comentarios dentro del JSON.
No uses markdown dentro del JSON.
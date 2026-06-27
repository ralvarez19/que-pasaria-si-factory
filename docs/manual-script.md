# Guion Manual Por JSON

El modo manual permite preparar todo el guion antes de generar video: tema, titulo, escenas, prompts visuales, narraciones y subtitulos.

## Ruta Por Defecto

Si existe este archivo, la app puede usarlo como guion manual:

```text
data/input/manual_script.json
```

Tambien puedes pasar otra ruta con la API o scripts.

## Formato

```json
{
  "topic": "¿Qué pasaría si la Luna desapareciera?",
  "title": "¿Qué pasaría si la Luna desapareciera?",
  "duration_seconds": 60,
  "scene_duration_seconds": 4,
  "language": "es",
  "aspect_ratio": "16:9",
  "width": 1280,
  "height": 720,
  "fps": 25,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "visual_prompt": "A cinematic realistic view of planet Earth from space as the Moon slowly fades away, dramatic documentary style.",
      "narration": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio",
      "subtitle": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio"
    }
  ]
}
```

## Validar

```powershell
.\scripts\validate-script.ps1 -ScriptPath "data/input/manual_script.json"
```

O por API:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/scripts/validate -Body (@{ script_path = "data/input/manual_script.json" } | ConvertTo-Json) -ContentType "application/json"
```

## Generar Desde JSON

```powershell
.\scripts\create-job-from-script.ps1 -ScriptPath "data/input/manual_script.json"
```

O por API:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/from-script -Body (@{ script_path = "data/input/manual_script.json" } | ConvertTo-Json) -ContentType "application/json"
```

`POST /api/v1/jobs` tambien acepta `script_path`, pero si pasas una ruta explicita y no existe, la API falla con un mensaje claro.

## Limites De Narracion

Para escenas de 4 segundos:

- `narration` debe tener entre 70 y 110 caracteres;
- `narration` debe tener entre 10 y 15 palabras;
- `subtitle` debe ser exactamente igual a `narration`;
- no uses varias oraciones largas;
- no uses `Cada consecuencia abre la puerta a la siguiente`;
- conserva tildes, ñ y signos `¿ ?`.

Ejemplos buenos:

```json
{"narration": "Sin la Luna, las mareas perderían fuerza y los océanos cambiarían para siempre", "subtitle": "Sin la Luna, las mareas perderían fuerza y los océanos cambiarían para siempre"}
```

```json
{"narration": "Después, la inclinación terrestre sería menos estable y el clima cambiaría poco a poco", "subtitle": "Después, la inclinación terrestre sería menos estable y el clima cambiaría poco a poco"}
```

## Salidas

El job guarda:

```text
data/jobs/{job_id}/script.json
data/jobs/{job_id}/input_script.json
```

`script.json` es el guion normalizado que usa el pipeline. `input_script.json` es una copia exacta del archivo manual usado.

## Errores Frecuentes

- `No existe el guion manual`: revisa la ruta enviada.
- `El guion manual debe incluir 'scenes' no vacio`: agrega al menos una escena.
- `La escena N no tiene visual_prompt`: completa el prompt visual.
- `La escena N tiene menos de 70 caracteres`: amplía la narracion.
- `La escena N supera 110 caracteres`: acorta la narracion.
- `La escena N tiene menos de 10 palabras`: agrega detalle documental.
- `La escena N supera 15 palabras`: reduce la frase.
- `La escena N tiene subtitle distinto de narration`: copia exactamente el mismo texto.

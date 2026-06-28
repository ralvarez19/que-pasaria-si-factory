# Qué pasaría si - Content Factory

API local para fabricar videos cortos de estilo documental a partir de un tema tipo:

```json
{"topic": "¿Qué pasaría si la Luna desapareciera?"}
```

El MVP crea un trabajo, planifica escenas, genera clips locales o reales con ComfyUI, crea audio silencioso o voz local por escena, escribe subtítulos SRT y ensambla un MP4 final con FFmpeg.
Opcionalmente envía el MP4 final por Telegram cuando `TELEGRAM_ENABLED=true`.

## Arquitectura

Tema -> Planner -> escenas -> VideoProvider -> TTSProvider -> SRT -> FFmpeg -> `data/jobs/{job_id}/final/final.mp4`

- `MockPlannerProvider`: funciona sin conexión.
- `OllamaPlannerProvider`: opcional con `OLLAMA_BASE_URL` y `OLLAMA_MODEL`.
- `PlaceholderVideoProvider`: genera clips de prueba con FFmpeg.
- `ComfyUIVideoProvider`: usa `POST /prompt` e `/history/{prompt_id}`.
- `SilentTTSProvider`: crea audio silencioso para validar el pipeline.
- `ComfyUITTSProvider`: genera voz local por escena con un workflow API de ComfyUI.
- `TelegramNotifier`: envía `final.mp4` por Telegram sin fallar el job si Telegram responde con error.
- SQLite persiste jobs y escenas.
- Un worker asyncio procesa una escena de video a la vez.

## Instalación

```powershell
scripts\setup.ps1
scripts\check-environment.ps1
```

## Ejecución

```powershell
cd "C:\ProyectosIA\que-pasaria-si-factory"
.\scripts\run-dev.ps1

scripts\run-dev.ps1
```

Swagger queda disponible en:

http://127.0.0.1:8000/docs

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Configuración

Copia `.env.example` a `.env` con `scripts\setup.ps1` y ajusta:

- `PLANNER_PROVIDER=mock` u `ollama`
- `VIDEO_PROVIDER=placeholder` o `comfyui`
- `TTS_PROVIDER=silent` o `comfyui`
- `TTS_AUDIO_FORMAT=flac`
- `TTS_SCENE_MODE=per_scene`
- `TELEGRAM_ENABLED=false`
- `TELEGRAM_BOT_TOKEN=`
- `TELEGRAM_CHAT_ID=`
- `TELEGRAM_SEND_AS_VIDEO=true`
- `COMFYUI_BASE_URL=http://127.0.0.1:8188`
- `COMFYUI_VIDEO_WORKFLOW=workflows/video/ltx23_t2v_api.json`
- `COMFYUI_TTS_WORKFLOW=workflows/audio/chatterbox_tts_api.json`
- `FFMPEG_PATH=ffmpeg`

## ComfyUI

Inicia ComfyUI normalmente en:

http://127.0.0.1:8188

Exporta el workflow en formato API desde ComfyUI y colócalo en:

`workflows/video/ltx23_t2v_api.json`

Copia `config/workflow_bindings.example.json` como `config/workflow_bindings.json` y completa los node IDs e input names reales. La API no inventa identificadores: si faltan workflow o bindings, el job falla con un error descriptivo.

## Texto A Voz Con ComfyUI

Guarda el workflow API de Chatterbox TTS en:

`workflows/audio/chatterbox_tts_api.json`

Inspecciona posibles bindings:

```powershell
scripts\inspect-tts-workflow.ps1
```

Completa la sección `tts` en `config/workflow_bindings.json` con los node IDs reales para texto, filename prefix y seed si existe. Luego activa:

```env
TTS_PROVIDER=comfyui
TTS_AUDIO_FORMAT=flac
TTS_SCENE_MODE=per_scene
```

Prueba una narración corta con la API activa:

```powershell
scripts\test-tts.ps1 -Text "¿Qué pasaría si la Luna desapareciera de repente?"
```

## Telegram

Para enviar el MP4 final automáticamente:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=token_del_bot
TELEGRAM_CHAT_ID=chat_id_destino
TELEGRAM_SEND_AS_VIDEO=true
```

Prueba un archivo existente:

```powershell
scripts\send-telegram-test.ps1 -VideoPath "C:\ruta\final.mp4" -Caption "Prueba de envío"
```

También puedes reintentar manualmente:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/{job_id}/send-telegram
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/latest/send-telegram
```

El envío automático usa el MP4 real del job en `data/jobs/{job_id}/final/final.mp4`. Para reenviar, abrir o inspeccionar el último render:

```powershell
scripts\send-latest-telegram.ps1
scripts\open-latest-video.ps1
scripts\show-last-job.ps1
```

Guía completa: `docs/telegram.md`.

## Crear Un Trabajo

```powershell
$body = @{
  topic = "¿Qué pasaría si la Luna desapareciera?"
  duration_seconds = 60
  scene_duration_seconds = 4
  language = "es"
  aspect_ratio = "16:9"
  width = 1280
  height = 720
  fps = 25
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/jobs -Body $body -ContentType "application/json"
```

También puedes pasar un guion manual:

```powershell
$body = @{
  topic = "¿Qué pasaría si la Luna desapareciera?"
  duration_seconds = 60
  scene_duration_seconds = 4
  script_path = "data/input/manual_script.json"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/jobs -Body $body -ContentType "application/json"
```

Si existe `data/input/manual_script.json`, la API lo usa automáticamente. Si pasas un `script_path` explícito y el archivo no existe, la API falla con un mensaje claro.

Validar y crear desde JSON:

```powershell
scripts\validate-script.ps1 -ScriptPath "data/input/manual_script.json"
scripts\create-job-from-script.ps1 -ScriptPath "data/input/manual_script.json"
```

Endpoints disponibles:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/scripts/validate -Body (@{ script_path = "data/input/manual_script.json" } | ConvertTo-Json) -ContentType "application/json"
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/from-script -Body (@{ script_path = "data/input/manual_script.json" } | ConvertTo-Json) -ContentType "application/json"
```

Guía completa: `docs/manual-script.md`.

## Lote De Guiones Manuales

Coloca varios JSON en:

`data/input/manual_scripts/pending`

Ejecuta:

```powershell
scripts\process-manual-scripts.ps1
scripts\show-manual-batch-status.ps1
```

Endpoints:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/batch/manual-scripts/run
Invoke-RestMethod http://127.0.0.1:8000/api/v1/batch/manual-scripts/status
```

Los archivos terminados se mueven a `done` con un `.result.json`; los fallidos se mueven a `failed` con un `.error.json`. Guía completa: `docs/manual-batch.md`.

## Reglas De Guion

Para escenas de 4 segundos, la API valida y corrige el plan antes de generar:

- título normalizado como `¿Qué pasaría si ...?`;
- narraciones manuales de una sola idea, entre 60 y 115 caracteres para escenas de 4 segundos;
- eliminación de `Cada consecuencia abre la puerta a la siguiente`;
- `subtitle` exactamente igual a `narration`;
- limpieza previa al TTS de saltos de línea, puntos internos, `;` y `:`.

Consultar progreso:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/jobs/{job_id}
Invoke-RestMethod http://127.0.0.1:8000/api/v1/jobs/{job_id}/scenes
```

Descargar:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/jobs/{job_id}/download -OutFile final.mp4
```

## Salidas

Cada trabajo crea:

`data/jobs/{job_id}/job.json`
`data/jobs/{job_id}/script.json`
`data/jobs/{job_id}/input_script.json`
`data/jobs/{job_id}/scenes/`
`data/jobs/{job_id}/clips/`
`data/jobs/{job_id}/audio/`
`data/jobs/{job_id}/subtitles/final.srt`
`data/jobs/{job_id}/temp/`
`data/jobs/{job_id}/final/final.mp4`
`data/jobs/{job_id}/logs/job.log`

Después de ensamblar correctamente el MP4, también se copia a:

`data/outputs/latest/final.mp4`
`data/outputs/archive/YYYYMMDD_HHmmss_{topic_slug}_{job_id_short}.mp4`

## Errores Frecuentes

- `FFmpeg no esta disponible`: instala FFmpeg o ajusta `FFMPEG_PATH`.
- `Falta el archivo requerido`: coloca el workflow o `config/workflow_bindings.json`.
- `No existe el nodo`: revisa el node ID exportado desde ComfyUI.
- `ComfyUI no responde`: inicia ComfyUI y confirma `COMFYUI_BASE_URL`.
- El modo por defecto `VIDEO_PROVIDER=placeholder` no usa ComfyUI; cambia a `comfyui` para LTX-2.3 real.
- `ComfyUI TTS termino... pero no se encontro audio`: revisa el nodo final del workflow TTS y sus bindings.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest
```

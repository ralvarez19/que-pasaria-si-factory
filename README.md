# Qué pasaría si - Content Factory

API local para fabricar videos cortos de estilo documental a partir de un tema tipo:

```json
{"topic": "¿Qué pasaría si la Luna desapareciera?"}
```

El MVP crea un trabajo, planifica escenas, genera clips de prueba locales, crea audio silencioso por escena, escribe subtítulos SRT y ensambla un MP4 final con FFmpeg. La integración real con ComfyUI queda preparada para activarse al colocar el workflow API y completar los bindings.

## Arquitectura

Tema -> Planner -> escenas -> VideoProvider -> TTSProvider -> SRT -> FFmpeg -> `data/jobs/{job_id}/final/final.mp4`

- `MockPlannerProvider`: funciona sin conexión.
- `OllamaPlannerProvider`: opcional con `OLLAMA_BASE_URL` y `OLLAMA_MODEL`.
- `PlaceholderVideoProvider`: genera clips de prueba con FFmpeg.
- `ComfyUIVideoProvider`: usa `POST /prompt` e `/history/{prompt_id}`.
- `SilentTTSProvider`: crea audio silencioso para validar el pipeline.
- `ComfyUITTSProvider`: interfaz lista para el workflow de voz.
- SQLite persiste jobs y escenas.
- Un worker asyncio procesa una escena de video a la vez.

## Instalación

```powershell
scripts\setup.ps1
scripts\check-environment.ps1
```

## Ejecución

```powershell
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
`data/jobs/{job_id}/scenes/`
`data/jobs/{job_id}/clips/`
`data/jobs/{job_id}/audio/`
`data/jobs/{job_id}/subtitles/final.srt`
`data/jobs/{job_id}/temp/`
`data/jobs/{job_id}/final/final.mp4`
`data/jobs/{job_id}/logs/job.log`

## Errores Frecuentes

- `FFmpeg no esta disponible`: instala FFmpeg o ajusta `FFMPEG_PATH`.
- `Falta el archivo requerido`: coloca el workflow o `config/workflow_bindings.json`.
- `No existe el nodo`: revisa el node ID exportado desde ComfyUI.
- `ComfyUI no responde`: inicia ComfyUI y confirma `COMFYUI_BASE_URL`.
- El modo por defecto `VIDEO_PROVIDER=placeholder` no usa ComfyUI; cambia a `comfyui` para LTX-2.3 real.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest
```

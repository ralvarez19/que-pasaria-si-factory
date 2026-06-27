# ComfyUI TTS

## Objetivo

Generar narración local por escena con ComfyUI y ensamblarla en el MP4 final con FFmpeg.

## Crear Y Exportar El Workflow

1. Crea o carga un workflow de Chatterbox TTS en ComfyUI.
2. Verifica que reciba texto como input editable.
3. Verifica que guarde un archivo de audio, idealmente WAV.
4. Exporta el workflow en formato API.
5. Guarda el JSON en `workflows/audio/chatterbox_tts_api.json`.

## Inspeccionar Node IDs

```powershell
scripts\inspect-tts-workflow.ps1
```

Busca:

- nodo/input de texto;
- nodo/input de `filename_prefix` o ruta de salida;
- nodo/input de seed si existe.

## Completar Bindings

Edita `config/workflow_bindings.json`:

```json
"tts": {
  "text_node_id": "...",
  "text_input_name": "...",
  "filename_node_id": "...",
  "filename_input_name": "...",
  "seed_node_id": "",
  "seed_input_name": ""
}
```

Si el workflow no tiene seed, deja `seed_node_id` y `seed_input_name` vacíos.

## Activar

```env
TTS_PROVIDER=comfyui
COMFYUI_TTS_WORKFLOW=workflows/audio/chatterbox_tts_api.json
TTS_AUDIO_FORMAT=wav
TTS_SCENE_MODE=per_scene
```

## Probar Una Narración

Con la API activa:

```powershell
scripts\test-tts.ps1 -Text "¿Qué pasaría si la Luna desapareciera de repente?"
```

## Generar Video Con Voz

Usa el endpoint normal de jobs. Cada escena toma `scene.narration`, envía TTS a ComfyUI y guarda:

```text
data/jobs/{job_id}/audio/scene_001.wav
```

FFmpeg normaliza cada audio a la duración de su escena: rellena con silencio si queda corto y recorta si queda largo.

## Errores Frecuentes

- `Falta el archivo requerido`: no existe `workflows/audio/chatterbox_tts_api.json`.
- `config/workflow_bindings.json debe contener la seccion 'tts'`: faltan bindings TTS.
- `Un binding no tiene node_id configurado`: completa node IDs reales.
- `ComfyUI TTS termino... pero no se encontro audio`: revisa que el nodo final guarde audio y aparezca en `/history/{prompt_id}`.
- `FFmpeg no esta disponible`: instala FFmpeg o ajusta `FFMPEG_PATH`.

# Workflow De ComfyUI

## Exportar En Formato API

1. Abre ComfyUI.
2. Carga el workflow que ya genera LTX-2.3 a 1280x720, 25 FPS y 4 segundos.
3. Activa el modo developer si hace falta.
4. Usa `Save (API Format)` o exporta el prompt API.
5. Guarda el JSON en `workflows/video/ltx23_t2v_api.json`.

## Bindings

Copia:

```powershell
Copy-Item config\workflow_bindings.example.json config\workflow_bindings.json
```

Completa en `config/workflow_bindings.json`:

- `prompt_node_id` y `prompt_input_name`
- `width_node_id` y `width_input_name`
- `height_node_id` y `height_input_name`
- `duration_node_id` y `duration_input_name`
- `fps_node_id` y `fps_input_name`
- `seed_node_id` y `seed_input_name`
- `filename_node_id` y `filename_input_name`

Los valores se cambian cargando el JSON como objeto Python. No se hacen reemplazos de texto.

## Activar Video Real

En `.env`:

```env
VIDEO_PROVIDER=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
```

Si faltan workflow o bindings, el job falla con mensaje claro y la API sigue iniciando.

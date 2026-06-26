# Qué pasaría si - Content Factory

Fábrica local de contenido para generar videos de tipo:

- ¿Qué pasaría si...?
- Curiosidades científicas
- Historias visuales
- Videos cortos para Reels, TikTok, Shorts y Facebook

## Flujo previsto

Tema -> guion -> escenas -> ComfyUI -> voz -> subtítulos -> FFmpeg -> video final.

## ComfyUI

Servidor esperado:

http://127.0.0.1:8188

## Workflows

Colocar el workflow de video exportado en formato API en:

workflows/video/ltx23_t2v_api.json

Colocar el workflow local de voz en:

workflows/audio/chatterbox_tts_api.json

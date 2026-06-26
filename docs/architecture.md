# Arquitectura

El MVP separa contratos de API, persistencia y proveedores para que la cola local pueda migrarse después a Redis, Celery u otro sistema.

## Componentes

- `app/main.py`: crea FastAPI, inicializa SQLite y arranca el worker.
- `app/api/v1.py`: endpoints REST.
- `app/models/job.py`: modelos SQLAlchemy para trabajos y escenas.
- `app/providers/planner.py`: planner mock y planner Ollama.
- `app/providers/video.py`: video placeholder y ComfyUI.
- `app/providers/tts.py`: audio silencioso y futura voz vía ComfyUI.
- `app/services/worker.py`: worker secuencial persistente.
- `app/services/ffmpeg.py`: normaliza, concatena y exporta MP4 final.
- `app/services/subtitles.py`: genera SRT global.
- `app/services/workflow.py`: modifica workflows como JSON estructurado.

## Estados

Jobs: `queued`, `planning`, `generating_video`, `generating_audio`, `assembling`, `completed`, `failed`, `cancelled`.

Escenas: `pending`, `generating`, `completed`, `failed`, `skipped`.

Al reiniciar la API, los trabajos que estaban en ejecución se marcan como `failed` con un mensaje recuperable para usar `/retry`.

## Concurrencia

El worker procesa un job a la vez y las escenas en orden. No se generan 15 clips en paralelo.

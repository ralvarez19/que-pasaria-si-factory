# Lote De Guiones Manuales

El procesamiento por lote toma varios JSON manuales y los ejecuta uno por uno. No inicia el siguiente archivo hasta que el job actual termina y Telegram queda registrado como `sent`, `failed` o `disabled`.

## Carpetas

Coloca los JSON nuevos en:

```text
data/input/manual_scripts/pending
```

La app crea y usa estas carpetas:

```text
data/input/manual_scripts/pending
data/input/manual_scripts/processing
data/input/manual_scripts/done
data/input/manual_scripts/failed
```

## Ejecutar

```powershell
.\scripts\process-manual-scripts.ps1
```

Con una carpeta distinta:

```powershell
.\scripts\process-manual-scripts.ps1 -ScriptsDir "data/input/manual_scripts/pending"
```

Por API:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/batch/manual-scripts/run -Body (@{ scripts_dir = "data/input/manual_scripts/pending"; stop_on_error = $false } | ConvertTo-Json) -ContentType "application/json"
```

## Estado

```powershell
.\scripts\show-manual-batch-status.ps1
Invoke-RestMethod http://127.0.0.1:8000/api/v1/batch/manual-scripts/status
```

El estado muestra el archivo actual, job actual, conteos de pending/processing/done/failed y el ultimo error.

## Archivos Done Y Failed

Cuando empieza un archivo:

```text
pending/01_luna.json -> processing/01_luna.json
```

Si termina bien:

```text
processing/01_luna.json -> done/YYYYMMDD_HHmm_01_luna.json
done/YYYYMMDD_HHmm_01_luna.result.json
```

Si falla:

```text
processing/01_luna.json -> failed/YYYYMMDD_HHmm_01_luna.json
failed/YYYYMMDD_HHmm_01_luna.error.json
```

El `.result.json` incluye `job_id`, `topic`, `title`, rutas de video, estado de Telegram y tiempos. El `.error.json` incluye el error y traceback.

## Corregir Fallidos

Abre el JSON movido a `failed`, corrige el problema indicado en el `.error.json`, y vuelve a copiarlo a `pending` con el nombre que prefieras.

## tts_text

Cada escena puede incluir:

```json
{
  "narration": "Al principio, el cielo perdería su punto más familiar. La noche cambia mucho",
  "subtitle": "Al principio, el cielo perdería su punto más familiar. La noche cambia mucho",
  "tts_text": "Al principio, el cielo perdería su punto más familiar, la noche cambia mucho"
}
```

`subtitle` se usa para el SRT y puede tener puntuación normal. `tts_text` se limpia y se envía a ChatterBox TTS. Si no incluyes `tts_text`, la app lo deriva desde `narration`.

Los puntos se limpian solo para TTS porque ChatterBox puede cortar la lectura con puntos, puntos suspensivos o varias frases. El subtítulo original no se modifica.

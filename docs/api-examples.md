# Ejemplos API

## Crear Job

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

## Listar Jobs

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/jobs
```

## Ver Progreso

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/jobs/{job_id}
Invoke-RestMethod http://127.0.0.1:8000/api/v1/jobs/{job_id}/scenes
```

## Cancelar

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/{job_id}/cancel
```

## Reintentar

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/{job_id}/retry
```

## Descargar

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/jobs/{job_id}/download -OutFile final.mp4
```

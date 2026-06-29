# ElevenLabs TTS

ElevenLabs es opcional. ComfyUI TTS sigue disponible como fallback.

## Configuracion

En `.env`:

```env
TTS_PROVIDER=auto
ELEVENLABS_ENABLED=true
ELEVENLABS_API_KEY=tu_api_key
ELEVENLABS_VOICE_ID=tu_voice_id
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_STABILITY=0.45
ELEVENLABS_SIMILARITY_BOOST=0.75
ELEVENLABS_STYLE=0.25
ELEVENLABS_USE_SPEAKER_BOOST=true
ELEVENLABS_TIMEOUT_SECONDS=120
ELEVENLABS_FALLBACK_TO_COMFYUI=true
```

No subas la API key a git. Los scripts solo muestran si existe, no su valor.

## Modos

- `TTS_PROVIDER=auto`: usa ElevenLabs si esta habilitado y hay API key; si no, usa ComfyUI.
- `TTS_PROVIDER=elevenlabs`: intenta ElevenLabs; si falla y `ELEVENLABS_FALLBACK_TO_COMFYUI=true`, usa ComfyUI.
- `TTS_PROVIDER=comfyui`: usa ComfyUI TTS.
- `TTS_PROVIDER=silent`: crea audio silencioso.

## Probar Voz

Con la API activa:

```powershell
.\scripts\test-elevenlabs-tts.ps1 -Text "Esta es una prueba de voz con ElevenLabs"
```

O usando el provider configurado:

```powershell
.\scripts\test-tts.ps1 -Text "Esta es una prueba de voz" -Provider auto
```

El audio de prueba ElevenLabs se guarda en `data/temp/elevenlabs_test.mp3` o en la ruta devuelta por la API.

## Fallback

Si ElevenLabs devuelve `401`, `403`, `429`, timeout o error HTTP, se registra el error resumido y se intenta ComfyUI si el fallback esta habilitado.

Revisa:

```text
logs/app.log
data/jobs/{job_id}/logs/job.log
```

Por escena se guarda:

- `tts_provider_used`
- `tts_fallback_used`
- `raw_audio_path`
- `normalized_audio_path`
- `raw_audio_duration_seconds`
- `normalized_audio_duration_seconds`
- `audio_error`

## Manual Scripts

El pipeline usa `tts_text` si existe. Si no existe, lo deriva desde `narration`.

`subtitle` se mantiene para el SRT; `tts_text` se limpia para evitar cortes por puntos.

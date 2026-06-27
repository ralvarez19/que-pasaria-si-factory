# Envío Por Telegram

La fábrica puede enviar `data/jobs/{job_id}/final/final.mp4` por Telegram cuando un job termina correctamente. Cada job mantiene su carpeta histórica, y el último render también queda en `data/outputs/latest/final.mp4`.

## 1. Crear El Bot

1. Abre Telegram y conversa con `@BotFather`.
2. Ejecuta `/newbot`.
3. Copia el token del bot. No lo compartas ni lo subas a git.

## 2. Obtener El Chat ID

1. Envía un mensaje al bot desde el chat destino.
2. Consulta:

```powershell
Invoke-RestMethod "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

3. Busca `message.chat.id` en la respuesta.

## 3. Configurar `.env`

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:token_real
TELEGRAM_CHAT_ID=123456789
TELEGRAM_SEND_AS_VIDEO=true
```

`TELEGRAM_SEND_AS_VIDEO=true` usa `sendVideo`. Si Telegram rechaza el archivo como video, la app reintenta como `sendDocument`.

## 4. Rutas De Salida

Cada job conserva su video en:

```text
data/jobs/{job_id}/final/final.mp4
```

Después del ensamblado, la app también copia el MP4 a:

```text
data/outputs/latest/final.mp4
data/outputs/archive/YYYYMMDD_HHmmss_{topic_slug}_{job_id_short}.mp4
```

El envío automático usa primero la ruta real del job, no la carpeta `latest`.

## 5. Probar Un Envío Directo

```powershell
.\scripts\send-telegram-test.ps1 -VideoPath "C:\ruta\final.mp4" -Caption "Prueba de envío"
```

El script lee `.env`, envía el archivo con HTTP multipart y no imprime el token completo.

## 6. Envío Automático

Con `TELEGRAM_ENABLED=true`, el worker envía el MP4 después de:

1. generar clips;
2. generar audio por escena;
3. ensamblar `final.mp4`;
4. copiar `latest` y `archive`;
5. guardar el job como `completed`.

Antes de enviar, valida que el archivo exista, tenga tamaño mayor a cero y pueda abrirse para lectura. Si Telegram falla, reintenta una vez mas despues de esperar. El job se mantiene `completed`. El error queda en `telegram_error`, `job.json`, `logs/app.log` y `data/jobs/{job_id}/logs/job.log`.

## 7. Reintento Manual

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/{job_id}/send-telegram
```

Ese endpoint envia exactamente `data/jobs/{job_id}/final/final.mp4`.

Para reenviar el último render:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/jobs/latest/send-telegram
.\scripts\send-latest-telegram.ps1
```

Para abrir el último video o inspeccionar el último job:

```powershell
.\scripts\open-latest-video.ps1
.\scripts\show-last-job.ps1
```

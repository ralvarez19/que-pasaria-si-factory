$ErrorActionPreference = "Continue"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

function Test-Ok($Name, $Ok, $Detail) {
    if ($Ok) {
        Write-Host "[OK] $Name - $Detail" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $Name - $Detail" -ForegroundColor Yellow
    }
}

$python = Get-Command py -ErrorAction SilentlyContinue
Test-Ok "Python launcher" ($null -ne $python) "py disponible"

if (Test-Path ".venv\Scripts\python.exe") {
    $version = & ".venv\Scripts\python.exe" --version
    Test-Ok "Python venv" $true $version
} else {
    Test-Ok "Python venv" $false "Ejecuta scripts\setup.ps1"
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
Test-Ok "FFmpeg" ($null -ne $ffmpeg) ($(if ($ffmpeg) { $ffmpeg.Source } else { "No encontrado en PATH" }))

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -UseBasicParsing -TimeoutSec 3
    Test-Ok "ComfyUI" ($response.StatusCode -lt 500) "http://127.0.0.1:8188 disponible"
} catch {
    Test-Ok "ComfyUI" $false "No responde en http://127.0.0.1:8188"
}

Test-Ok "Workflow video" (Test-Path "workflows\video\ltx23_t2v_api.json") "workflows\video\ltx23_t2v_api.json"
Test-Ok "Bindings activos" (Test-Path "config\workflow_bindings.json") "config\workflow_bindings.json"
Test-Ok "Bindings ejemplo" (Test-Path "config\workflow_bindings.example.json") "config\workflow_bindings.example.json"
Test-Ok "Base de datos" (Test-Path "data\content_factory.db") "Se crea automaticamente al iniciar la API si no existe"

New-Item -ItemType Directory -Force logs, data\jobs, data\outputs, data\outputs\latest, data\outputs\archive, data\temp, data\input\manual_scripts\pending, data\input\manual_scripts\processing, data\input\manual_scripts\done, data\input\manual_scripts\failed, workflows\video, workflows\audio | Out-Null
Test-Ok "Carpetas de salida" $true "logs, data\jobs, data\outputs\latest, data\outputs\archive, data\input\manual_scripts"

$envValues = @{}
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $envValues[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
}
$ttsProvider = $envValues["TTS_PROVIDER"]
if (!$ttsProvider) { $ttsProvider = "silent" }
Test-Ok "TTS provider" $true $ttsProvider
$elevenEnabled = $envValues["ELEVENLABS_ENABLED"]
if (!$elevenEnabled) { $elevenEnabled = "false" }
$elevenKey = $envValues["ELEVENLABS_API_KEY"]
$elevenVoice = $envValues["ELEVENLABS_VOICE_ID"]
Test-Ok "ElevenLabs enabled" $true $elevenEnabled
Test-Ok "ElevenLabs API key" (![string]::IsNullOrWhiteSpace($elevenKey)) ($(if ($elevenKey) { "Configurada (oculta)" } else { "No configurada" }))
Test-Ok "ElevenLabs voice id" (![string]::IsNullOrWhiteSpace($elevenVoice)) ($(if ($elevenVoice) { "Configurado" } else { "No configurado" }))

$telegramEnabled = $envValues["TELEGRAM_ENABLED"]
if (!$telegramEnabled) { $telegramEnabled = "false" }
$telegramToken = $envValues["TELEGRAM_BOT_TOKEN"]
$telegramChatId = $envValues["TELEGRAM_CHAT_ID"]
Test-Ok "Telegram enabled" $true $telegramEnabled
Test-Ok "Telegram bot token" (![string]::IsNullOrWhiteSpace($telegramToken)) ($(if ($telegramToken) { "Configurado (oculto)" } else { "No configurado" }))
Test-Ok "Telegram chat id" (![string]::IsNullOrWhiteSpace($telegramChatId)) ($(if ($telegramChatId) { "Configurado parcialmente: $($telegramChatId.Substring(0, [Math]::Min(3, $telegramChatId.Length)))..." } else { "No configurado" }))

$ttsWorkflow = $envValues["COMFYUI_TTS_WORKFLOW"]
if (!$ttsWorkflow) { $ttsWorkflow = "workflows/audio/chatterbox_tts_api.json" }
$ttsWorkflowExists = Test-Path $ttsWorkflow
if ($ttsProvider -eq "comfyui") {
    Test-Ok "Workflow TTS" $ttsWorkflowExists $ttsWorkflow
    $ttsBindingsOk = $false
    if (Test-Path "config\workflow_bindings.json") {
        try {
            $bindings = Get-Content -Raw -Encoding UTF8 "config\workflow_bindings.json" | ConvertFrom-Json
            $ttsBindingsOk = $bindings.tts -and $bindings.tts.text_node_id -and $bindings.tts.text_input_name -and $bindings.tts.filename_node_id -and $bindings.tts.filename_input_name
        } catch {
            $ttsBindingsOk = $false
        }
    }
    Test-Ok "Bindings TTS" $ttsBindingsOk "tts.text_node_id/text_input_name/filename_node_id/filename_input_name"
    if ($ttsWorkflowExists) {
        try {
            $workflow = Get-Content -Raw -Encoding UTF8 $ttsWorkflow | ConvertFrom-Json
            $hasText = $false
            $hasAudioSave = $false
            foreach ($nodeProperty in $workflow.PSObject.Properties) {
                $node = $nodeProperty.Value
                $classType = [string]$node.class_type
                if ($classType -match "(?i)text|prompt|tts|chatterbox") { $hasText = $true }
                if ($classType -match "(?i)save.*audio|audio.*save|wav|sound") { $hasAudioSave = $true }
                if ($node.inputs) {
                    foreach ($inputProperty in $node.inputs.PSObject.Properties) {
                        if ($inputProperty.Name -match "(?i)text|prompt|sentence|narration") { $hasText = $true }
                        if ($inputProperty.Name -match "(?i)filename|prefix|path") { $hasAudioSave = $true }
                    }
                }
            }
            Test-Ok "Workflow TTS texto/audio" ($hasText -and $hasAudioSave) "nodo de texto=$hasText, nodo/archivo de audio=$hasAudioSave"
        } catch {
            Test-Ok "Workflow TTS texto/audio" $false "No se pudo inspeccionar el JSON"
        }
    }
} elseif ($ttsProvider -in @("auto", "elevenlabs")) {
    Test-Ok "Workflow TTS fallback ComfyUI" $ttsWorkflowExists $ttsWorkflow
}

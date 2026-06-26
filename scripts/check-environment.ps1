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

New-Item -ItemType Directory -Force logs, data\jobs, data\outputs, data\temp, workflows\video, workflows\audio | Out-Null
Test-Ok "Carpetas de salida" $true "logs, data\jobs, data\outputs, data\temp"

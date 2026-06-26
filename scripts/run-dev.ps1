$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "No existe el entorno virtual. Ejecuta scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
}

$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

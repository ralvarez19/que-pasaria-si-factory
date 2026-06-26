$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "No existe el entorno virtual. Ejecuta scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}

& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

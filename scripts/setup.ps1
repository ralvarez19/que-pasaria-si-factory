$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

if (!(Test-Path ".venv")) {
    py -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
}

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "Configuración terminada." -ForegroundColor Green

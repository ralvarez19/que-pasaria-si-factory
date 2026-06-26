$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

if (!(Test-Path ".venv")) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        py -m venv .venv
    }
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
}

New-Item -ItemType Directory -Force logs, data\jobs, data\outputs, data\temp, workflows\video, workflows\audio | Out-Null

Write-Host "Configuracion terminada." -ForegroundColor Green
Write-Host "Ejecuta scripts\check-environment.ps1 para validar dependencias externas." -ForegroundColor Cyan

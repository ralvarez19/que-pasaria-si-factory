$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

$latest = Join-Path (Get-Location) "data\outputs\latest\final.mp4"
if (-not (Test-Path $latest)) {
    throw "No existe el ultimo video: $latest"
}

Start-Process -FilePath $latest

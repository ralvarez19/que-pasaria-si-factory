$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

$jobsRoot = Join-Path (Get-Location) "data\jobs"
$latest = Join-Path (Get-Location) "data\outputs\latest\final.mp4"
if (-not (Test-Path $jobsRoot)) {
    throw "No existe data\jobs"
}

$lastJobFile = Get-ChildItem -Path $jobsRoot -Filter "job.json" -Recurse |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $lastJobFile) {
    throw "No se encontro ningun job.json"
}

$job = Get-Content -Raw -Encoding UTF8 $lastJobFile.FullName | ConvertFrom-Json
Write-Host "job_id: $($job.id)"
Write-Host "topic: $($job.topic)"
Write-Host "status: $($job.status)"
Write-Host "final_video_path: $($job.final_video_path)"
Write-Host "telegram_status: $($job.telegram_status)"
Write-Host "telegram_error: $($job.telegram_error)"
Write-Host "latest: $latest"

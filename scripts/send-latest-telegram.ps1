param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Net.Http
Set-Location "$PSScriptRoot\.."

$latest = Join-Path (Get-Location) "data\outputs\latest\final.mp4"
if (-not (Test-Path $latest)) {
    throw "No existe el ultimo video: $latest"
}

$client = [System.Net.Http.HttpClient]::new()
try {
    $response = $client.PostAsync("$BaseUrl/api/v1/jobs/latest/send-telegram", $null).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error enviando latest por Telegram: HTTP $([int]$response.StatusCode) $body"
    }
    $result = $body | ConvertFrom-Json
    Write-Host "status: $($result.status)"
    Write-Host "method: $($result.method)"
    Write-Host "video_path: $($result.video_path)"
    Write-Host "telegram_message_id: $($result.telegram_message_id)"
} finally {
    $client.Dispose()
}

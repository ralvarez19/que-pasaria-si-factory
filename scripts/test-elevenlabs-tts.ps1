param(
    [Parameter(Mandatory = $true)]
    [string]$Text,

    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Net.Http
Set-Location "$PSScriptRoot\.."

$client = [System.Net.Http.HttpClient]::new()
try {
    $payload = @{ text = $Text; provider = "elevenlabs" } | ConvertTo-Json -Compress
    $content = [System.Net.Http.StringContent]::new($payload, [System.Text.Encoding]::UTF8, "application/json")
    $response = $client.PostAsync("$BaseUrl/api/v1/tts/test", $content).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error probando ElevenLabs TTS: HTTP $([int]$response.StatusCode) $body"
    }
    $result = $body | ConvertFrom-Json
    Write-Host "audio_path: $($result.audio_path)"
    Write-Host "provider_used: $($result.provider_used)"
    Write-Host "fallback_used: $($result.fallback_used)"
    Write-Host "duration_seconds: $($result.duration_seconds)"
    if (Test-Path $result.audio_path) {
        $size = (Get-Item $result.audio_path).Length
        Write-Host "size_bytes: $size"
    }
} finally {
    $client.Dispose()
}

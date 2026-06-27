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

$client = [System.Net.Http.HttpClient]::new()
try {
    $payload = @{ text = $Text } | ConvertTo-Json -Compress
    $content = [System.Net.Http.StringContent]::new($payload, [System.Text.Encoding]::UTF8, "application/json")
    $response = $client.PostAsync("$BaseUrl/api/v1/tts/test", $content).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error probando TTS: HTTP $([int]$response.StatusCode) $body"
    }
    $result = $body | ConvertFrom-Json
    Write-Host "audio_path: $($result.audio_path)"
    Write-Host "prompt_id: $($result.prompt_id)"
} finally {
    $client.Dispose()
}

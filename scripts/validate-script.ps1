param(
    [string]$ScriptPath = "data/input/manual_script.json",
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
    $payload = @{ script_path = $ScriptPath } | ConvertTo-Json -Compress
    $content = [System.Net.Http.StringContent]::new($payload, [System.Text.Encoding]::UTF8, "application/json")
    $response = $client.PostAsync("$BaseUrl/api/v1/scripts/validate", $content).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error validando script: HTTP $([int]$response.StatusCode) $body"
    }
    $result = $body | ConvertFrom-Json
    Write-Host "ok: $($result.ok)"
    Write-Host "script_path: $($result.script_path)"
    Write-Host "topic: $($result.topic)"
    Write-Host "title: $($result.title)"
    Write-Host "scene_count: $($result.scene_count)"
    if ($result.warnings.Count -gt 0) {
        Write-Host "warnings:"
        $result.warnings | ForEach-Object { Write-Host "- $_" -ForegroundColor Yellow }
    }
    if ($result.errors.Count -gt 0) {
        Write-Host "errors:"
        $result.errors | ForEach-Object { Write-Host "- $_" }
        exit 1
    }
} finally {
    $client.Dispose()
}

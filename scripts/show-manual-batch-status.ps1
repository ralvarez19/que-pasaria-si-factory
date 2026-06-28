param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Net.Http

$client = [System.Net.Http.HttpClient]::new()
try {
    $response = $client.GetAsync("$BaseUrl/api/v1/batch/manual-scripts/status").GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error consultando batch: HTTP $([int]$response.StatusCode) $body"
    }
    $status = $body | ConvertFrom-Json
    Write-Host "running: $($status.running)"
    Write-Host "current_file: $($status.current_file)"
    Write-Host "current_job_id: $($status.current_job_id)"
    Write-Host "pending: $($status.pending_count)"
    Write-Host "processing: $($status.processing_count)"
    Write-Host "done: $($status.done_count)"
    Write-Host "failed: $($status.failed_file_count)"
    Write-Host "processed_count: $($status.processed_count)"
    Write-Host "failed_count: $($status.failed_count)"
    Write-Host "videos_generated: $($status.videos_generated)"
    Write-Host "telegram_sent: $($status.telegram_sent)"
    Write-Host "last_error: $($status.last_error)"
} finally {
    $client.Dispose()
}

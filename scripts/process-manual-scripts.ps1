param(
    [string]$ScriptsDir = "data/input/manual_scripts/pending",
    [switch]$StopOnError,
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
    $payload = @{
        scripts_dir = $ScriptsDir
        stop_on_error = [bool]$StopOnError
    } | ConvertTo-Json -Compress
    $content = [System.Net.Http.StringContent]::new($payload, [System.Text.Encoding]::UTF8, "application/json")
    $response = $client.PostAsync("$BaseUrl/api/v1/batch/manual-scripts/run", $content).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Error iniciando batch: HTTP $([int]$response.StatusCode) $body"
    }
    Write-Host "Batch iniciado"

    while ($true) {
        Start-Sleep -Seconds 2
        $statusResponse = $client.GetAsync("$BaseUrl/api/v1/batch/manual-scripts/status").GetAwaiter().GetResult()
        $statusBody = $statusResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $statusResponse.IsSuccessStatusCode) {
            throw "Error consultando batch: HTTP $([int]$statusResponse.StatusCode) $statusBody"
        }
        $status = $statusBody | ConvertFrom-Json
        Write-Host "running=$($status.running) current_file=$($status.current_file) current_job=$($status.current_job_id) pending=$($status.pending_count) done=$($status.done_count) failed=$($status.failed_file_count)"
        if (-not $status.running) {
            Write-Host "procesados: $($status.processed_count)"
            Write-Host "fallidos: $($status.failed_count)"
            Write-Host "videos_generados: $($status.videos_generated)"
            Write-Host "telegram_enviados: $($status.telegram_sent)"
            Write-Host "ultimo_error: $($status.last_error)"
            break
        }
    }
} finally {
    $client.Dispose()
}

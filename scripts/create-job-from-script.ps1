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

function Invoke-JsonPost($Client, $Url, $Payload) {
    $json = $Payload | ConvertTo-Json -Depth 10 -Compress
    $content = [System.Net.Http.StringContent]::new($json, [System.Text.Encoding]::UTF8, "application/json")
    $response = $Client.PostAsync($Url, $content).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "HTTP $([int]$response.StatusCode) $body"
    }
    return $body | ConvertFrom-Json
}

$client = [System.Net.Http.HttpClient]::new()
try {
    $validation = Invoke-JsonPost $client "$BaseUrl/api/v1/scripts/validate" @{ script_path = $ScriptPath }
    if (-not $validation.ok) {
        Write-Host "Script invalido:"
        $validation.errors | ForEach-Object { Write-Host "- $_" }
        exit 1
    }
    if ($validation.warnings.Count -gt 0) {
        Write-Host "Warnings:"
        $validation.warnings | ForEach-Object { Write-Host "- $_" -ForegroundColor Yellow }
    }

    $created = Invoke-JsonPost $client "$BaseUrl/api/v1/jobs/from-script" @{ script_path = $ScriptPath }
    $jobId = $created.job_id
    Write-Host "job_id: $jobId"

    while ($true) {
        Start-Sleep -Seconds 2
        $jobResponse = $client.GetAsync("$BaseUrl/api/v1/jobs/$jobId").GetAwaiter().GetResult()
        $jobBody = $jobResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $jobResponse.IsSuccessStatusCode) {
            throw "Error consultando job: HTTP $([int]$jobResponse.StatusCode) $jobBody"
        }
        $job = $jobBody | ConvertFrom-Json
        Write-Host "status: $($job.status)"
        if ($job.status -in @("completed", "failed", "cancelled")) {
            Write-Host "final_video_path: $($job.final_video_path)"
            $latest = Join-Path (Get-Location) "data\outputs\latest\final.mp4"
            Write-Host "latest_copied: $(Test-Path $latest)"
            Write-Host "latest_path: $latest"
            Write-Host "telegram_status: $($job.telegram_status)"
            Write-Host "telegram_error: $($job.telegram_error)"
            break
        }
    }
} finally {
    $client.Dispose()
}

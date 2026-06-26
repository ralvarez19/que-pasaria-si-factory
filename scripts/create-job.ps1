param(
    [Parameter(Mandatory = $true)]
    [string]$Topic,

    [int]$DurationSeconds = 60,
    [int]$SceneDurationSeconds = 4,
    [int]$Width = 1280,
    [int]$Height = 720,
    [int]$Fps = 25,
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Net.Http

$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(30)

try {
    $payload = [ordered]@{
        topic = $Topic
        duration_seconds = $DurationSeconds
        scene_duration_seconds = $SceneDurationSeconds
        language = "es"
        aspect_ratio = "16:9"
        width = $Width
        height = $Height
        fps = $Fps
    }

    $json = $payload | ConvertTo-Json -Depth 10 -Compress
    $content = [System.Net.Http.StringContent]::new($json, [System.Text.Encoding]::UTF8, "application/json")
    $createResponse = $client.PostAsync("$BaseUrl/api/v1/jobs", $content).GetAwaiter().GetResult()
    $createBody = $createResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()

    if (-not $createResponse.IsSuccessStatusCode) {
        throw "Error creando job: HTTP $([int]$createResponse.StatusCode) $createBody"
    }

    $created = $createBody | ConvertFrom-Json
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
            Write-Host "topic: $($job.topic)"
            Write-Host "title: $($job.title)"
            if ($job.final_video_path) {
                Write-Host "final_video_path: $($job.final_video_path)"
            }
            if ($job.error_message) {
                Write-Host "error_message: $($job.error_message)"
            }
            break
        }
    }
} finally {
    $client.Dispose()
}

param(
    [Parameter(Mandatory = $true)]
    [string]$JobId,

    [string]$BaseUrl = "http://127.0.0.1:8000",
    [double]$ToleranceSeconds = 0.35
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

function Get-VideoProbe($Path) {
    $json = & ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of json "$Path"
    if ($LASTEXITCODE -ne 0) {
        throw "ffprobe fallo para $Path"
    }
    $data = $json | ConvertFrom-Json
    $stream = $data.streams[0]
    $parts = ([string]$stream.r_frame_rate).Split("/")
    $fps = 0
    if ($parts.Length -eq 2 -and [double]$parts[1] -ne 0) {
        $fps = [double]$parts[0] / [double]$parts[1]
    }
    return [pscustomobject]@{
        duration = [double]$stream.duration
        fps = $fps
        width = [int]$stream.width
        height = [int]$stream.height
    }
}

$scenes = Invoke-RestMethod "$BaseUrl/api/v1/jobs/$JobId/scenes"
Write-Host "Scene | expected_seconds | real_seconds | fps | width | height | warning"
foreach ($scene in $scenes) {
    $warning = ""
    $realSeconds = $null
    $fps = $null
    $width = $null
    $height = $null
    if (-not $scene.video_path -or -not (Test-Path $scene.video_path)) {
        $warning = "missing video"
    } else {
        try {
            $probe = Get-VideoProbe $scene.video_path
            $realSeconds = [Math]::Round($probe.duration, 3)
            $fps = [Math]::Round($probe.fps, 3)
            $width = $probe.width
            $height = $probe.height
            if ([Math]::Abs($probe.duration - [double]$scene.duration_seconds) -gt $ToleranceSeconds) {
                $warning = "duration mismatch"
            }
        } catch {
            $warning = $_.Exception.Message
        }
    }
    Write-Host "$($scene.scene_number) | $($scene.duration_seconds) | $realSeconds | $fps | $width | $height | $warning"
}

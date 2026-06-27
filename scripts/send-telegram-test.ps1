param(
    [Parameter(Mandatory = $true)]
    [string]$VideoPath,

    [Parameter(Mandatory = $true)]
    [string]$Caption
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Net.Http
Set-Location "$PSScriptRoot\.."

function Read-DotEnv {
    $values = @{}
    if (Test-Path ".env") {
        Get-Content ".env" -Encoding UTF8 | ForEach-Object {
            if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
                $values[$matches[1].Trim()] = $matches[2].Trim().Trim('"')
            }
        }
    }
    return $values
}

function Send-TelegramFile($Client, $Token, $ChatId, $Path, $Text, $Method) {
    $fieldName = if ($Method -eq "sendVideo") { "video" } else { "document" }
    $url = "https://api.telegram.org/bot$Token/$Method"
    $form = [System.Net.Http.MultipartFormDataContent]::new()
    $fileStream = [System.IO.File]::OpenRead($Path)
    try {
        $fileContent = [System.Net.Http.StreamContent]::new($fileStream)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("video/mp4")
        $form.Add($fileContent, $fieldName, [System.IO.Path]::GetFileName($Path))
        $form.Add([System.Net.Http.StringContent]::new($ChatId, [System.Text.Encoding]::UTF8), "chat_id")
        $form.Add([System.Net.Http.StringContent]::new($Text, [System.Text.Encoding]::UTF8), "caption")
        $response = $Client.PostAsync($url, $form).GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        return [pscustomobject]@{
            Success = $response.IsSuccessStatusCode
            StatusCode = [int]$response.StatusCode
            Body = $body
            Method = $Method
        }
    } finally {
        $form.Dispose()
        $fileStream.Dispose()
    }
}

$envValues = Read-DotEnv
$token = $envValues["TELEGRAM_BOT_TOKEN"]
$chatId = $envValues["TELEGRAM_CHAT_ID"]
$sendAsVideo = $envValues["TELEGRAM_SEND_AS_VIDEO"]
if (!$sendAsVideo) { $sendAsVideo = "true" }

if (!$token) { throw "Falta TELEGRAM_BOT_TOKEN en .env" }
if (!$chatId) { throw "Falta TELEGRAM_CHAT_ID en .env" }
if (-not (Test-Path $VideoPath)) { throw "No existe el archivo: $VideoPath" }

$resolvedVideoPath = (Resolve-Path $VideoPath).Path
$method = if ($sendAsVideo.ToLowerInvariant() -eq "true") { "sendVideo" } else { "sendDocument" }
$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromMinutes(5)

try {
    Write-Host "Enviando $resolvedVideoPath con $method"
    $result = Send-TelegramFile $client $token $chatId $resolvedVideoPath $Caption $method
    if (-not $result.Success -and $method -eq "sendVideo") {
        Write-Warning "sendVideo fallo HTTP $($result.StatusCode). Reintentando con sendDocument."
        $result = Send-TelegramFile $client $token $chatId $resolvedVideoPath $Caption "sendDocument"
    }
    Write-Host "method: $($result.Method)"
    Write-Host "status_code: $($result.StatusCode)"
    Write-Host "response: $($result.Body)"
    if (-not $result.Success) {
        throw "Telegram respondio con error HTTP $($result.StatusCode)"
    }
} finally {
    $client.Dispose()
}

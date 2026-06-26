param(
    [string]$Workflow = "workflows/video/ltx23_t2v_api.json"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

if (!(Test-Path $Workflow)) {
    throw "No existe el workflow: $Workflow"
}

$json = Get-Content -Raw -Encoding UTF8 $Workflow | ConvertFrom-Json
$nodes = @()

foreach ($property in $json.PSObject.Properties) {
    $nodeId = $property.Name
    $node = $property.Value
    $classType = [string]$node.class_type
    $title = ""
    if ($node._meta -and $node._meta.title) {
        $title = [string]$node._meta.title
    }
    $inputs = @()
    if ($node.inputs) {
        foreach ($inputProperty in $node.inputs.PSObject.Properties) {
            $inputs += [pscustomobject]@{
                Name = $inputProperty.Name
                Value = $inputProperty.Value
            }
        }
    }
    $nodes += [pscustomobject]@{
        NodeId = $nodeId
        ClassType = $classType
        Title = $title
        Inputs = $inputs
    }
}

function Format-InputSummary($Inputs) {
    (($Inputs | ForEach-Object {
        $value = $_.Value
        if ($value -is [array]) {
            $valueText = ($value -join ",")
        } else {
            $valueText = [string]$value
        }
        "$($_.Name)=$valueText"
    }) -join "; ")
}

function Show-Section($Title, $Items) {
    Write-Host ""
    Write-Host "## $Title" -ForegroundColor Cyan
    if (!$Items -or $Items.Count -eq 0) {
        Write-Host "(ninguno)"
        return
    }
    $Items | Select-Object NodeId, ClassType, Title, @{Name = "Inputs"; Expression = { Format-InputSummary $_.Inputs }} | Format-Table -Wrap -AutoSize
}

$textNodes = $nodes | Where-Object {
    $_.ClassType -match "Text|CLIP|Prompt|String" -or ($_.Inputs | Where-Object { $_.Name -match "text|prompt" })
}
$videoNodes = $nodes | Where-Object {
    $_.ClassType -match "Video|LTXV|Sampler|VAE" -or ($_.Inputs | Where-Object { $_.Name -match "video|latent_image|frames|fps|frame_rate|length" })
}
$imageNodes = $nodes | Where-Object {
    $_.ClassType -match "LoadImage|Image|ImgToVideo|I2V" -or ($_.Inputs | Where-Object { $_.Name -match "image|first_frame|last_frame|reference_image|init_image" })
}
$outputNodes = $nodes | Where-Object {
    $_.ClassType -match "Save|Preview|Output"
}

$hardcodedImages = foreach ($node in $nodes) {
    foreach ($input in $node.Inputs) {
        $value = [string]$input.Value
        if ($value -match "(?i)(^photo_|\.jpg$|\.jpeg$|\.png$|\.webp$)") {
            [pscustomobject]@{
                NodeId = $node.NodeId
                ClassType = $node.ClassType
                Input = $input.Name
                Value = $value
            }
        }
    }
}

$frameInputs = foreach ($node in $nodes) {
    foreach ($input in $node.Inputs) {
        if ($input.Name -match "(?i)first_frame|last_frame|reference_image|init_image|start_image|end_image") {
            [pscustomobject]@{
                NodeId = $node.NodeId
                ClassType = $node.ClassType
                Input = $input.Name
                Value = [string]$input.Value
            }
        }
    }
}

Show-Section "Nodos de texto" $textNodes
Show-Section "Nodos de video" $videoNodes
Show-Section "Nodos de imagen" $imageNodes
Show-Section "Nodos de salida" $outputNodes

Write-Host ""
Write-Host "## Archivos de imagen hardcodeados" -ForegroundColor Cyan
if ($hardcodedImages.Count -eq 0) {
    Write-Host "(ninguno)"
} else {
    $hardcodedImages | Format-Table -Wrap -AutoSize
}

Write-Host ""
Write-Host "## Posibles first_frame / last_frame / reference_image" -ForegroundColor Cyan
if ($frameInputs.Count -eq 0) {
    Write-Host "(ninguno)"
} else {
    $frameInputs | Format-Table -Wrap -AutoSize
}

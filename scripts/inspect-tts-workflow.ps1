param(
    [string]$Workflow = "workflows/audio/chatterbox_tts_api.json",
    [string]$Bindings = "config/workflow_bindings.json"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location "$PSScriptRoot\.."

if (!(Test-Path $Workflow)) {
    throw "No existe el workflow de TTS: $Workflow"
}

$workflowJson = Get-Content -Raw -Encoding UTF8 $Workflow | ConvertFrom-Json
$bindingLabels = @{}
if (Test-Path $Bindings) {
    $bindingsJson = Get-Content -Raw -Encoding UTF8 $Bindings | ConvertFrom-Json
    if ($bindingsJson.tts) {
        foreach ($name in @("text", "filename", "format", "seed")) {
            $nodeField = "${name}_node_id"
            $inputField = "${name}_input_name"
            $nodeId = $bindingsJson.tts.$nodeField
            $inputName = $bindingsJson.tts.$inputField
            if ($nodeId -and $inputName) {
                $bindingLabels["$nodeId|$inputName"] = $name
            }
        }
    }
}

Write-Host "Node ID | class_type | input | valor actual | posible binding"
Write-Host "--- | --- | --- | --- | ---"

foreach ($property in $workflowJson.PSObject.Properties) {
    $nodeId = $property.Name
    $node = $property.Value
    $classType = [string]$node.class_type
    if (!$node.inputs) { continue }
    foreach ($inputProperty in $node.inputs.PSObject.Properties) {
        $inputName = $inputProperty.Name
        $value = [string]$inputProperty.Value
        $binding = $bindingLabels["$nodeId|$inputName"]
        if (!$binding) {
            if ($inputName -match "(?i)text|prompt|sentence|narration") { $binding = "text?" }
            elseif ($inputName -match "(?i)filename|prefix|path|file") { $binding = "filename?" }
            elseif ($inputName -match "(?i)format|codec|extension") { $binding = "format?" }
            elseif ($inputName -match "(?i)seed") { $binding = "seed?" }
        }
        Write-Host "$nodeId | $classType | $inputName | $value | $binding"
    }
}

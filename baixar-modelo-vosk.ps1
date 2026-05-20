$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Models = Join-Path $Root "models"
$Zip = Join-Path $Models "vosk-model-small-pt-0.3.zip"
$ModelDir = Join-Path $Models "vosk-model-small-pt-0.3"

New-Item -ItemType Directory -Force -Path $Models | Out-Null

if (-not (Test-Path -LiteralPath $ModelDir)) {
  if (-not (Test-Path -LiteralPath $Zip)) {
    Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip" -OutFile $Zip
  }

  Expand-Archive -LiteralPath $Zip -DestinationPath $Models -Force
}

Write-Host "Modelo Vosk instalado em: $ModelDir"

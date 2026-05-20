$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $Root "config.json"
$ExampleConfigPath = Join-Path $Root "config.example.json"

Write-Host "== Local Ditado installer =="

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
  throw "Python nao encontrado no PATH. Instale Python 3.11+ e tente novamente."
}

Write-Host "Python: $Python"
python --version

Write-Host "`nInstalando dependencias principais..."
python -m pip install -r (Join-Path $Root "requirements.txt")

$HasNvidia = $false
try {
  nvidia-smi | Out-Null
  $HasNvidia = $true
} catch {
  $HasNvidia = $false
}

if ($HasNvidia) {
  $InstallGpu = Read-Host "GPU NVIDIA detectada. Instalar dependencias CUDA? [S/n]"
  if ($InstallGpu -eq "" -or $InstallGpu.ToLowerInvariant().StartsWith("s")) {
    python -m pip install --extra-index-url https://pypi.ngc.nvidia.com -r (Join-Path $Root "requirements-gpu-cu12.txt")
  }
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
  Copy-Item -LiteralPath $ExampleConfigPath -Destination $ConfigPath
}

Write-Host "`nMicrofones encontrados:"
python (Join-Path $Root "diagnostico.py") --devices-only

$DeviceName = Read-Host "`nDigite parte do nome do microfone [External Mic]"
if ($DeviceName -eq "") {
  $DeviceName = "External Mic"
}

$Profile = Read-Host "Perfil: precisao, equilibrado ou rapido [precisao]"
if ($Profile -eq "") {
  $Profile = "precisao"
}

$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$Config | Add-Member -NotePropertyName device_name -NotePropertyValue $DeviceName -Force
$Config | Add-Member -NotePropertyName active_profile -NotePropertyValue $Profile -Force
if ($HasNvidia) {
  $Config | Add-Member -NotePropertyName whisper_device -NotePropertyValue "cuda" -Force
  $Config | Add-Member -NotePropertyName whisper_compute_type -NotePropertyValue "int8_float16" -Force
} else {
  $Config | Add-Member -NotePropertyName whisper_device -NotePropertyValue "cpu" -Force
  $Config | Add-Member -NotePropertyName whisper_compute_type -NotePropertyValue "int8" -Force
}
$Config | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host "`nConfig salva em: $ConfigPath"

$InstallVosk = Read-Host "Baixar modelo Vosk de fallback? [s/N]"
if ($InstallVosk.ToLowerInvariant().StartsWith("s")) {
  powershell -ExecutionPolicy Bypass -File (Join-Path $Root "baixar-modelo-vosk.ps1")
}

powershell -ExecutionPolicy Bypass -File (Join-Path $Root "instalar-autostart.ps1")

$InstallTray = Read-Host "Instalar icone de bandeja no login? [S/n]"
if ($InstallTray -eq "" -or $InstallTray.ToLowerInvariant().StartsWith("s")) {
  powershell -ExecutionPolicy Bypass -File (Join-Path $Root "instalar-tray-autostart.ps1")
}

Write-Host "`nInstalacao concluida."
Write-Host "Use Ctrl+Alt+D para iniciar/parar o ditado."

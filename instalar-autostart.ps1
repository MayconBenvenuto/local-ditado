$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pythonw = "C:\Users\benve\AppData\Local\Programs\Python\Python312\pythonw.exe"
$Script = Join-Path $Root "dictado_hotkey.py"
$Prompt = Join-Path $Root "prompts\pt-br-default.txt"
$Model = Join-Path $Root "models\vosk-model-pt-fb-v0.1.1-20220516_2113"
if (-not (Test-Path -LiteralPath $Model)) {
  $Model = Join-Path $Root "models\vosk-model-small-pt-0.3"
}
$TaskName = "VoskLocalDictado"

if (-not (Test-Path -LiteralPath $Pythonw)) {
  throw "pythonw.exe nao encontrado em $Pythonw"
}

if (-not (Test-Path -LiteralPath $Script)) {
  throw "Script nao encontrado em $Script"
}

$Arguments = "`"$Script`" --device-name `"External Mic`" --engine whisper --whisper-model small --whisper-device cuda --whisper-compute-type int8_float16 --silence-seconds 2.5 --beam-size 5 --cpu-threads 8 --initial-prompt-file `"$Prompt`" --model `"$Model`""
$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument $Arguments -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0)

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "Ditado local instalado e iniciado."
Write-Host "Atalho: Ctrl+Alt+D para iniciar/parar e colar no campo focado."
Write-Host "Microfone: External Mic"
Write-Host "Modelo: $Model"
Write-Host "Motor: Whisper small local com GPU"
Write-Host "Parada por silencio: 2.5s"

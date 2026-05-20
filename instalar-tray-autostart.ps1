$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pythonw = Join-Path (Split-Path (Get-Command python).Source -Parent) "pythonw.exe"
$Script = Join-Path $Root "tray_app.py"
$TaskName = "LocalDitadoTray"

if (-not (Test-Path -LiteralPath $Pythonw)) {
  throw "pythonw.exe nao encontrado ao lado do Python ativo."
}

if (-not (Test-Path -LiteralPath $Script)) {
  throw "Tray app nao encontrado em $Script"
}

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$Script`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0)

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "Tray do Local Ditado instalado e iniciado."

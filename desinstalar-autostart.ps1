$ErrorActionPreference = "Stop"

$TaskNames = @("LocalDitado", "LocalDitadoTray", "VoskLocalDictado")

foreach ($TaskName in $TaskNames) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
}

Write-Host "Local Ditado removido do inicio do Windows."

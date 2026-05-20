$ErrorActionPreference = "Stop"

$TaskName = "VoskLocalDictado"

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Ditado local removido do inicio do Windows."

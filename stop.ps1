$ErrorActionPreference = "SilentlyContinue"

Get-Process -Name "celery" | Stop-Process -Force
$celeryPids = (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "celery\s+-A\s+notif\.celery:app\s+worker" }).ProcessId
if ($celeryPids) { $celeryPids | ForEach-Object { Stop-Process -Id $_ -Force } }

$runserverPids = (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "manage\.py\s+runserver" }).ProcessId
if ($runserverPids) { $runserverPids | ForEach-Object { Stop-Process -Id $_ -Force } }

Write-Host "Stopped."

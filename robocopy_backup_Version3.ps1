# robocopy_backup.ps1
param(
  [string]$Source = 'C:\OCR_BEST\Ticket_system',
  [string]$DestBase = 'C:\Backup',
  [int]$Threads = 8,
  [int]$Retries = 2,
  [int]$WaitSeconds = 5
)

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Dest = Join-Path $DestBase "Ticket_system_$timestamp"
New-Item -ItemType Directory -Path $Dest -Force | Out-Null

$excludeDirs = @('.git','venv','node_modules')
$excludePaths = $excludeDirs | ForEach-Object { Join-Path $Source $_ }

$logFile = Join-Path $Dest 'robocopy.log'
$args = @(
  $Source,
  $Dest,
  '/E',
  "/MT:$Threads",
  "/R:$Retries",
  "/W:$WaitSeconds",
  '/COPY:DAT',
  '/DCOPY:T',
  "/LOG:$logFile",
  '/NP',
  '/TEE'
)

if ($excludePaths.Count -gt 0) {
  $args += '/XD'
  $args += $excludePaths
}

Write-Host "Source: $Source"
Write-Host "Destination: $Dest"
Write-Host "Log: $logFile"
Write-Host "Running robocopy..."

$proc = Start-Process -FilePath 'robocopy' -ArgumentList $args -NoNewWindow -Wait -PassThru
$exit = $proc.ExitCode

if ($exit -lt 8) {
  Write-Host "Robocopy completed. Exit code: $exit"
  Write-Host "Backup location: $Dest"
  exit 0
} else {
  Write-Error "Robocopy failed. Exit code: $exit. Проверьте лог: $logFile"
  exit $exit
}
param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path,
  [string]$Python = "python",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$backend = Join-Path $ProjectRoot "backend"
$logs = Join-Path $backend "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
  foreach ($pidValue in ($conn | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Stop-Process -Id $pidValue -Force
  }
  Start-Sleep -Seconds 1
}

Start-Process `
  -FilePath $Python `
  -ArgumentList @("manage.py", "runserver", "0.0.0.0:$Port", "--noreload") `
  -WorkingDirectory $backend `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logs "runserver.out.log") `
  -RedirectStandardError (Join-Path $logs "runserver.err.log")

Start-Sleep -Seconds 3
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Select-Object -First 1 LocalAddress,LocalPort,OwningProcess

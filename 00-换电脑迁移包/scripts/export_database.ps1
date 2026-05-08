param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Read-EnvFile($Path) {
  $data = @{}
  if (!(Test-Path -LiteralPath $Path)) {
    return $data
  }
  foreach ($line in Get-Content -Encoding UTF8 -LiteralPath $Path) {
    $text = $line.Trim()
    if (!$text -or $text.StartsWith("#") -or !$text.Contains("=")) {
      continue
    }
    if ($text.StartsWith("export ")) {
      $text = $text.Substring(7).Trim()
    }
    $parts = $text.Split("=", 2)
    $value = $parts[1].Trim()
    if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    $data[$parts[0].Trim()] = $value
  }
  return $data
}

$envMap = Read-EnvFile (Join-Path $ProjectRoot "backend\.env")
$dbName = if ($envMap.ContainsKey("MYSQL_DB")) { $envMap["MYSQL_DB"] } else { "wxappEnglishlearn" }
$dbUser = if ($envMap.ContainsKey("MYSQL_USER")) { $envMap["MYSQL_USER"] } else { "root" }
$dbPass = if ($envMap.ContainsKey("MYSQL_PASSWORD")) { $envMap["MYSQL_PASSWORD"] } else { "199977" }
$dbHost = if ($envMap.ContainsKey("MYSQL_HOST")) { $envMap["MYSQL_HOST"] } else { "127.0.0.1" }
$dbPort = if ($envMap.ContainsKey("MYSQL_PORT")) { $envMap["MYSQL_PORT"] } else { "3306" }

if (!$OutFile) {
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $packageRoot = Resolve-Path "$PSScriptRoot\.."
  $OutFile = Join-Path $packageRoot "database\$dbName-$stamp.sql"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null

$mysqlDump = Get-Command mysqldump -ErrorAction SilentlyContinue
if (!$mysqlDump) {
  throw "mysqldump not found. Add MySQL Server bin directory to PATH or export with MySQL Workbench."
}

$env:MYSQL_PWD = $dbPass
try {
  & $mysqlDump.Source `
    "--host=$dbHost" `
    "--port=$dbPort" `
    "--user=$dbUser" `
    "--default-character-set=utf8mb4" `
    "--single-transaction" `
    "--routines" `
    "--triggers" `
    "--events" `
    $dbName | Out-File -Encoding UTF8 -LiteralPath $OutFile
} finally {
  Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
}

Write-Host "Database exported: $OutFile"

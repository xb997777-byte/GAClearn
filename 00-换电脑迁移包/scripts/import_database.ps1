param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path,
  [string]$SqlFile = "",
  [switch]$CreateDatabase
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

if (!$SqlFile) {
  $packageRoot = Resolve-Path "$PSScriptRoot\.."
  $latest = Get-ChildItem -LiteralPath (Join-Path $packageRoot "database") -Filter "*.sql" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (!$latest) {
    throw "SQL file not found. Put .sql under package database directory or pass -SqlFile."
  }
  $SqlFile = $latest.FullName
}

$mysql = Get-Command mysql -ErrorAction SilentlyContinue
if (!$mysql) {
  throw "mysql not found. Add MySQL Server bin directory to PATH."
}

$env:MYSQL_PWD = $dbPass
try {
  if ($CreateDatabase) {
    & $mysql.Source "--host=$dbHost" "--port=$dbPort" "--user=$dbUser" "--default-character-set=utf8mb4" `
      -e "CREATE DATABASE IF NOT EXISTS ``$dbName`` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  }
  Get-Content -Raw -Encoding UTF8 -LiteralPath $SqlFile | & $mysql.Source "--host=$dbHost" "--port=$dbPort" "--user=$dbUser" "--default-character-set=utf8mb4" $dbName
} finally {
  Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
}

Write-Host "Database imported: $dbName <= $SqlFile"

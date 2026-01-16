param(
    [string]$Module = "api",
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $OutFile = Join-Path $RepoRoot ("logs\\importtime_{0}.txt" -f $Module)
} elseif (-not [System.IO.Path]::IsPathRooted($OutFile)) {
    $OutFile = Join-Path $RepoRoot $OutFile
}

$OutDir = Split-Path -Parent $OutFile
if ($OutDir -and -not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$importCmd = "import $Module"

$prevErrorAction = $ErrorActionPreference
$prevNativePref = $null
$hasNativePref = Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue
if ($hasNativePref) {
    $prevNativePref = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}

try {
    $ErrorActionPreference = "Continue"
    & python -X importtime -c $importCmd 2>&1 | Out-File -FilePath $OutFile -Encoding utf8
}
finally {
    $ErrorActionPreference = $prevErrorAction
    if ($hasNativePref) {
        $PSNativeCommandUseErrorActionPreference = $prevNativePref
    }
}

Write-Host ("Saved import-time report to {0}" -f $OutFile)

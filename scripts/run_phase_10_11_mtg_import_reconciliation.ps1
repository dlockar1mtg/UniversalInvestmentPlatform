param(
    [string]$MtgPackagePath = "",
    [string]$DatabasePath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $MtgPackagePath) {
    $CandidatePaths = @(
        (Join-Path (Split-Path $RepoRoot -Parent) "mtg-investment-terminal\data\validation\phase_10\universal_export\latest"),
        "C:\Users\DevonLockard\mtg-investment-terminal\data\validation\phase_10\universal_export\latest"
    )
    $MtgPackagePath = $CandidatePaths |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1
}

if (-not $MtgPackagePath -or -not (Test-Path $MtgPackagePath)) {
    throw "Certified MTG Phase 10.10 package not found. Pass -MtgPackagePath with the universal_export\latest directory."
}

$RequiredSourceFiles = @(
    "asset_master.csv",
    "forecasts.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "portfolio_summary.csv",
    "platform_status.csv",
    "diagnostics.csv",
    "export_manifest.json",
    "package_summary.json"
)

foreach ($Name in $RequiredSourceFiles) {
    $Path = Join-Path $MtgPackagePath $Name
    if (-not (Test-Path $Path)) {
        throw "Missing certified MTG source file: $Path"
    }
}

Write-Host "Phase 10.11 source package"
Write-Host (Resolve-Path $MtgPackagePath)
Write-Host ""

Write-Host "Running focused Phase 10.11 tests..."
python -m pytest .\tests\test_phase_10_11_mtg_import_reconciliation.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Arguments = @(
    ".\scripts\run_phase_10_11_mtg_import_reconciliation.py",
    "--source-package",
    (Resolve-Path $MtgPackagePath).Path
)

if ($DatabasePath) {
    $Arguments += @("--database", $DatabasePath)
}

Write-Host ""
Write-Host "Adapting, importing, and reconciling MTG package..."
python @Arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ReportRoot = ".\data\validation\imports\mtg_phase_10_11"
$ReportPath = Join-Path $ReportRoot "PHASE_10_11_MTG_IMPORT_RECONCILIATION.md"
$JsonPath = Join-Path $ReportRoot "phase_10_11_mtg_import_reconciliation.json"

Write-Host ""
Write-Host "Certification"
Get-Content $ReportPath

Write-Host ""
Write-Host "Reconciliation JSON"
Get-Content $JsonPath

Write-Host ""
Write-Host "Repository status"
git status --short

Write-Host ""
Write-Host "Staged files"
git diff --cached --name-only

Write-Host ""
Write-Host "Generated integration packages, DuckDB files, and validation reports remain local and must not be staged."

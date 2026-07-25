[CmdletBinding()]
param(
    [string]$MetalsRoot = "C:\Users\DevonLockard\metals",
    [string]$Owner = "Devon Lockard",
    [string]$NotificationDestination = "local-console",
    [switch]$SkipExport,
    [switch]$SkipLiveProviders
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepositoryRoot

$Arguments = @(
    "scripts\run_metals_production_cycle.py",
    "--metals-root", $MetalsRoot,
    "--owner", $Owner,
    "--notification-destination", $NotificationDestination
)

if ($SkipExport) {
    $Arguments += "--skip-export"
}
if ($SkipLiveProviders) {
    $Arguments += "--skip-live-providers"
}

Write-Host "========================================================================"
Write-Host "Universal Investment Platform - Metals Production Cycle"
Write-Host "========================================================================"
Write-Host "Repository: $RepositoryRoot"
Write-Host "Metals root: $MetalsRoot"
Write-Host ""

& python @Arguments
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Error "Metals production cycle failed with exit code $ExitCode."
    exit $ExitCode
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "Metals Operations Visibility Publication"
Write-Host "========================================================================"

& python "scripts\publish_metals_operations_visibility.py"
$VisibilityExitCode = $LASTEXITCODE
if ($VisibilityExitCode -ne 0) {
    Write-Error "Metals operations visibility failed with exit code $VisibilityExitCode."
    exit $VisibilityExitCode
}

exit 0

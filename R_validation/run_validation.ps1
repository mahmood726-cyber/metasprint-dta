# MetaSprint DTA — R Validation Runner
# Usage: powershell -ExecutionPolicy Bypass -File run_validation.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rScript = Join-Path $scriptDir "validate_metasprint_dta.R"
$outputLog = Join-Path $scriptDir "validation_output.txt"

Write-Host "MetaSprint DTA R Validation" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Check R installation
$rPath = Get-Command Rscript -ErrorAction SilentlyContinue
if (-not $rPath) {
    Write-Host "ERROR: Rscript not found in PATH." -ForegroundColor Red
    Write-Host "Install R from https://cran.r-project.org/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using R: $($rPath.Source)" -ForegroundColor Green
Write-Host ""

# Run validation
Write-Host "Running validation script..." -ForegroundColor Yellow
& Rscript $rScript 2>&1 | Tee-Object -FilePath $outputLog

$exitCode = $LASTEXITCODE
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "Validation completed successfully." -ForegroundColor Green
    $jsonFile = Join-Path $scriptDir "validation_reference.json"
    if (Test-Path $jsonFile) {
        Write-Host "Reference JSON: $jsonFile" -ForegroundColor Green
    }
} else {
    Write-Host "Validation failed with exit code $exitCode" -ForegroundColor Red
}

Write-Host "Full output saved to: $outputLog" -ForegroundColor Cyan

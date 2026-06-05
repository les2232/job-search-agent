Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path (Join-Path $ProjectRoot "ui_app.py"))) {
    Write-Error "Could not find ui_app.py. Run this script from the job-search-agent repo or keep it under scripts\."
}

$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    . $ActivateScript
} else {
    Write-Host "No .venv found at $ProjectRoot\.venv"
    Write-Host "Create and install the environment with:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  python -m pip install -r requirements.txt"
    Write-Host ""
    Write-Host "Then rerun:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run_app.ps1"
    exit 1
}

python -m streamlit run ui_app.py

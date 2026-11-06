# Windows setup: creates .venv, installs CPU-only dependencies, downloads the model, runs a smoke check.
# Safe to run more than once.
# Usage: powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

function Invoke-Step([string]$Label, [scriptblock]$Command) {
    Write-Host "==> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Label (exit code $LASTEXITCODE)" }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Step "Create virtual environment (Python 3.12)" { py -3.12 -m venv .venv }
    } else {
        Invoke-Step "Create virtual environment (python on PATH)" { python -m venv .venv }
    }
}
$py = ".\.venv\Scripts\python.exe"
Invoke-Step "Check Python version" { & $py -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 is required, found ' + sys.version" }
Invoke-Step "Upgrade pip" { & $py -m pip install --quiet --upgrade pip }
Invoke-Step "Install PyTorch (CPU only)" { & $py -m pip install --quiet torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu }
Invoke-Step "Install dependencies" { & $py -m pip install --quiet -r requirements.txt -r requirements-dev.txt }
Invoke-Step "Install this package" { & $py -m pip install --quiet --no-deps -e . }
Invoke-Step "Download model (first run only, ~600 MB)" { & $py -m catalog_enrichment.download }
Invoke-Step "Smoke check" { & $py -m catalog_enrichment.smoke }
Write-Host "`nSetup complete. Start the app with: powershell -ExecutionPolicy Bypass -File .\run.ps1"

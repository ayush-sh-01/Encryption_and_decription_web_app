param(
    [int]$Port = 8000
)

# Ensure we run from the script directory so relative paths like requirements.txt work
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "Working directory: $PWD"

Write-Host "Creating virtual environment (if missing) and installing requirements..."
if (-not (Test-Path .venv)) {
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing requirements (may skip if already installed)..."
if (Test-Path requirements.txt) {
    pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found in $scriptDir - installing minimal packages"
    pip install fastapi uvicorn cryptography python-multipart
}

Write-Host "Starting server on http://127.0.0.1:${Port}/"
# Use the venv's python to run uvicorn so the command works even if uvicorn isn't on PATH
& .\.venv\Scripts\python.exe -m uvicorn app:app --reload --host 127.0.0.1 --port $Port

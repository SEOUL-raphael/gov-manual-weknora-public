param([string]$Python = 'python', [switch]$Offline)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python -c 'import sys; assert sys.version_info[:2] == (3,12)'
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 first.' }
if ($Offline) {
    & $Python scripts/verify_bundle.py
    if ($LASTEXITCODE -ne 0) { throw 'Bundle checksum verification failed' }
}
& $Python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
$taskPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
if ($Offline) {
    & $taskPython -m pip install --no-index --find-links wheels -r requirements.lock.txt
} else {
    & $taskPython -m pip install -r requirements.lock.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $taskPython scripts/init_config.py
if ($LASTEXITCODE -ne 0) { throw 'Configuration initialization failed' }
if ($Offline) {
    $taskDocker=(Get-Command docker -ErrorAction SilentlyContinue).Source
    if (-not $taskDocker) { $taskDocker='C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
    & $taskDocker load -i images.tar
    if ($LASTEXITCODE -ne 0) { throw 'Docker image import failed' }
} else {
    & $taskPython scripts/download_reranker.py
    if ($LASTEXITCODE -ne 0) { throw 'Reranker download failed' }
}
Write-Output 'Setup ready. Set API keys in .env, then run scripts/start.ps1. Model inference currently requires Internet.'

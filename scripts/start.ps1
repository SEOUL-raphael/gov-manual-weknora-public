$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$taskPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$taskDocker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $taskDocker) { $taskDocker = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements.txt first.' }
if (-not (Test-Path -LiteralPath '.env')) {
    & $taskPython scripts/init_config.py
    if ($LASTEXITCODE -ne 0) { throw 'Configuration initialization failed' }
}
& $taskDocker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine unavailable. Repair/start Docker Desktop, then run start.ps1 again.' }
& $taskDocker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration' }
& $taskDocker compose up -d --wait --wait-timeout 900
if ($LASTEXITCODE -ne 0) { throw 'WeKnora did not become healthy; inspect docker compose logs.' }
Get-Content -Raw config/index-2048.sql | & $taskDocker compose exec -T postgres sh -c 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { throw '2048-dimension index creation failed' }
& $taskPython scripts/bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'WeKnora bootstrap failed' }

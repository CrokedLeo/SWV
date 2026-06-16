param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..")
)

Write-Host "=== SWV Development Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create virtual environment
$venvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "  Virtual environment created at $venvPath" -ForegroundColor Green
} else {
    Write-Host "[1/5] Virtual environment already exists, skipping" -ForegroundColor Green
}

# Activate virtual environment
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
}

# Step 2: Install dependencies
Write-Host "[2/5] Installing dependencies..." -ForegroundColor Yellow
pip install -e ".[dev]"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "  Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 3: Copy .env.example to .env if needed
$envFile = Join-Path $ProjectRoot ".env"
$envExample = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path $envFile)) {
    Write-Host "[3/5] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item $envExample $envFile
    Write-Host "  .env file created - update with your configuration" -ForegroundColor Green
} else {
    Write-Host "[3/5] .env file already exists, skipping" -ForegroundColor Green
}

# Step 4: Initialize alembic migrations
$alembicDir = Join-Path $ProjectRoot "alembic"
if (-not (Test-Path "$alembicDir\alembic.ini") -and -not (Test-Path "$ProjectRoot\alembic.ini")) {
    Write-Host "[4/5] Initializing Alembic migrations..." -ForegroundColor Yellow
    alembic init alembic 2>$null
    Write-Host "  Alembic initialized" -ForegroundColor Green
} else {
    Write-Host "[4/5] Alembic already initialized, skipping" -ForegroundColor Green
}

# Step 5: Create uploads directory
$uploadsDir = Join-Path $ProjectRoot "uploads"
if (-not (Test-Path $uploadsDir)) {
    Write-Host "[5/5] Creating uploads directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $uploadsDir -Force | Out-Null
    Write-Host "  Uploads directory created at $uploadsDir" -ForegroundColor Green
} else {
    Write-Host "[5/5] Uploads directory already exists, skipping" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Activate the environment:  .\.venv\Scripts\Activate.ps1"
Write-Host "  2. Update configuration in:   .env"
Write-Host "  3. Start the server:          make dev"
Write-Host "  4. Run tests:                 make test"
Write-Host ""
Write-Host "For more targets:              make help"

#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== SWV Development Environment Setup ==="
echo ""

# Step 1: Create virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3.11 -m venv .venv
    echo "  Virtual environment created at .venv"
else
    echo "[1/5] Virtual environment already exists, skipping"
fi

# Activate virtual environment
source .venv/bin/activate

# Step 2: Install dependencies
echo "[2/5] Installing dependencies..."
pip install -e ".[dev]"
echo "  Dependencies installed successfully"

# Step 3: Copy .env.example to .env if needed
if [ ! -f ".env" ]; then
    echo "[3/5] Creating .env from .env.example..."
    cp .env.example .env
    echo "  .env file created - update with your configuration"
else
    echo "[3/5] .env file already exists, skipping"
fi

# Step 4: Initialize alembic migrations
if [ ! -d "alembic" ] && [ ! -f "alembic.ini" ]; then
    echo "[4/5] Initializing Alembic migrations..."
    alembic init alembic 2>/dev/null || true
    echo "  Alembic initialized"
else
    echo "[4/5] Alembic already initialized, skipping"
fi

# Step 5: Create uploads directory
if [ ! -d "uploads" ]; then
    echo "[5/5] Creating uploads directory..."
    mkdir -p uploads
    echo "  Uploads directory created at uploads"
else
    echo "[5/5] Uploads directory already exists, skipping"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Activate the environment:  source .venv/bin/activate"
echo "  2. Update configuration in:   .env"
echo "  3. Start the server:          make dev"
echo "  4. Run tests:                 make test"
echo ""
echo "For more targets:              make help"

#!/usr/bin/env pwsh
# RecoverAI Backend Startup Script (Windows PowerShell)

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot ".." "backend"
Set-Location $backendDir

Write-Host "=== RecoverAI Backend Startup ===" -ForegroundColor Cyan

# Copy .env if not exists
if (-not (Test-Path ".env")) {
    if (Test-Path "../.env.example") {
        Copy-Item "../.env.example" ".env"
        Write-Host "[INFO] Created .env from .env.example" -ForegroundColor Yellow
    }
}

# Check Python
$pythonVersion = python --version 2>&1
Write-Host "[INFO] $pythonVersion"

# Install dependencies
Write-Host "[INFO] Installing dependencies..."
pip install -r requirements.txt --quiet

# Initialize database
Write-Host "[INFO] Initializing database..."
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import init_db, engine, Base
import app.models

async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('[INFO] Database tables created')

asyncio.run(setup())
"

Write-Host "[INFO] Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host "[INFO] API docs available at http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to stop`n"

$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

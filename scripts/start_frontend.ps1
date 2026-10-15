#!/usr/bin/env pwsh
# RecoverAI Frontend Startup Script

$ErrorActionPreference = "Stop"
$frontendDir = Join-Path $PSScriptRoot ".." "frontend"
Set-Location $frontendDir

Write-Host "=== RecoverAI Frontend Startup ===" -ForegroundColor Cyan

if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing npm dependencies..."
    npm install
}

Write-Host "[INFO] Starting Vite dev server on http://localhost:5173" -ForegroundColor Green
Write-Host "[INFO] Proxy: /api/* → http://localhost:8000"
Write-Host "[INFO] Make sure the backend is running first!`n"

npm run dev

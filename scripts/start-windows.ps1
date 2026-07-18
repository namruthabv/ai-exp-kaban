$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
docker compose up --build --detach

$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/api/health" | Out-Null
        $healthy = $true
        break
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $healthy) {
    throw "The container started, but the health check did not become ready."
}

Write-Host "Project Management MVP is available at http://localhost:8000"

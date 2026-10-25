# BedrockKnowledgeBase Docker 起動
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".env")) {
    Copy-Item ".env.docker.example" ".env"
    Write-Host "Created .env from .env.docker.example"
}

New-Item -ItemType Directory -Force -Path "data\uploads" | Out-Null

docker compose up -d --build @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "UI:    http://localhost:3010/login"
Write-Host "API:   http://localhost:8180/docs"
Write-Host "Logs:  docker compose logs -f backend frontend"

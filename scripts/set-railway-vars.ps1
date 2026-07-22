# Requires: railway login && railway link
# Usage: .\scripts\set-railway-vars.ps1

$ErrorActionPreference = "Stop"

Write-Host "Setting BedrockKnowledgeBase Railway variables..."
railway variables set "USE_BEDROCK_MOCK=true"
railway variables set "CORS_ORIGINS=*"
railway variables set "DYNAMODB_ENDPOINT="
railway variables set "APP_ENV=production"
railway variables set "ENABLE_GUARDRAILS=true"
railway variables set "ENABLE_AGENTS=true"
railway variables set "AWS_REGION=ap-northeast-1"
# Next.js rewrite target inside the container (must match start.sh uvicorn)
railway variables set "INTERNAL_API_URL=http://127.0.0.1:8180"

Write-Host ""
Write-Host "Done. Optional next steps:"
Write-Host "  railway add --database postgres   # if not already added"
Write-Host "  railway variables                 # confirm"
Write-Host "  railway up                        # or Redeploy in dashboard"
Write-Host ""
Write-Host "For live Bedrock later, set USE_BEDROCK_MOCK=false and:"
Write-Host "  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY"
Write-Host "  BEDROCK_KNOWLEDGE_BASE_ID / BEDROCK_GUARDRAIL_ID / BEDROCK_AGENT_ID"

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.api.ai import router as ai_router
from src.config import get_settings
from src.db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    try:
        from src.scripts.init_dynamo import main as init_dyn

        init_dyn()
    except Exception:
        # Railway / no DynamoDB Local: seed in-memory prompts
        try:
            from src.services.prompts import seed_default_prompts

            seed_default_prompts()
        except Exception:
            pass
    yield


app = FastAPI(
    title="Bedrock Knowledge Base Platform",
    description=(
        "エンタープライズ向け生成AI: Text/Image/Embedding/Guardrails/"
        "Prompt Management/Model Evaluation + RAG/Agents"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
_cors = settings.cors_origin_list or ["*"]
_allow_all = "*" in _cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ai_router)


@app.get("/", response_class=HTMLResponse)
def root():
    return """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"/><title>BKB API</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;min-height:100vh;display:grid;place-items:center;
background:linear-gradient(160deg,#0b1220,#12344d);color:#e8f1f8}
main{width:min(560px,calc(100% - 2rem))}
a{color:#5ec8ff} h1 span{color:#5ec8ff}
</style></head><body><main>
<h1>Bedrock <span>KB</span> API</h1>
<p>S3 → Knowledge Base → Bedrock → Lambda → API Gateway → Web</p>
<ul>
<li><a href="http://localhost:3010">Web UI</a></li>
<li><a href="/docs">Swagger</a></li>
<li><a href="/health">Health</a></li>
<li><a href="/api/use-cases">Use cases</a></li>
</ul>
</main></body></html>"""


@app.get("/health")
def health():
    s = get_settings()
    return {
        "status": "ok",
        "app": "bedrock-knowledge-base",
        "mock_mode": s.mock_mode,
        "region": s.aws_region,
        "features": [
            "text_generation",
            "image_generation",
            "embedding",
            "guardrails",
            "prompt_management",
            "model_evaluation",
            "rag_knowledge_bases",
            "agents",
        ],
        "knowledge_base_configured": bool(s.bedrock_knowledge_base_id),
        "guardrail_configured": bool(s.bedrock_guardrail_id),
    }

"""FastAPI アプリケーション本体: ルーター登録・CORS・テレメトリ・ヘルスチェック。"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.api.ai import router as ai_router
from src.auth import install_auth_middleware
from src.config import get_settings
from src.db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    """起動時に DB・プロジェクト・DynamoDB/プロンプトを初期化する。"""
    init_database()
    try:
        from src.services.projects import seed_default_project

        seed_default_project()
    except Exception:
        pass
    try:
        from src.scripts.init_dynamo import main as init_dyn

        init_dyn()
    except Exception:
        try:
            from src.services.prompts import seed_default_prompts

            seed_default_prompts()
        except Exception:
            pass
    yield


app = FastAPI(
    title="Bedrock Knowledge Base Platform",
    description=(
        "受託/自社向け生成AI運用基盤: Text/Image/Embedding/Guardrails/"
        "Prompt/Evaluation/RAG/Agents + Projects/Telemetry/Feedback"
    ),
    version="0.2.0",
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
install_auth_middleware(app)


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    """/api/* リクエストのレイテンシとステータスをテレメトリに記録する。"""
    start = time.perf_counter()
    response = await call_next(request)
    if not get_settings().enable_telemetry:
        return response
    path = request.url.path
    if not path.startswith("/api/"):
        return response
    try:
        from src.services.telemetry import record_event

        project = getattr(request.state, "project", None) or {}
        record_event(
            path=path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=int((time.perf_counter() - start) * 1000),
            project_id=project.get("project_id"),
            mock=get_settings().mock_mode,
            meta={"env": get_settings().app_env},
        )
    except Exception:
        pass
    return response


app.include_router(ai_router)


@app.get("/", response_class=HTMLResponse)
def root():
    """トップページ（Web UI / Swagger / ヘルスへのリンク）。"""
    return """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"/><title>BKB API</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;min-height:100vh;display:grid;place-items:center;
background:linear-gradient(160deg,#0b1220,#12344d);color:#e8f1f8}
main{width:min(560px,calc(100% - 2rem))}
a{color:#5ec8ff} h1 span{color:#5ec8ff}
</style></head><body><main>
<h1>Bedrock <span>KB</span> API</h1>
<p>Prototype → Staging → Production · DS + Eng collaboration</p>
<ul>
<li><a href="http://localhost:3010">Web UI</a></li>
<li><a href="/docs">Swagger</a></li>
<li><a href="/health">Health</a></li>
<li><a href="/api/ops/summary">Ops summary</a></li>
</ul>
</main></body></html>"""


@app.get("/health")
def health():
    """サービス稼働状態と各機能の設定有無を返す。"""
    s = get_settings()
    from src.db import database_ping

    db = database_ping()
    return {
        "status": "ok" if db.get("ok") or not s.database_configured else "degraded",
        "app": "bedrock-knowledge-base",
        "version": "0.2.0",
        "app_env": s.app_env,
        "mock_mode": s.mock_mode,
        "llm_provider": s.llm_provider,
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
            "projects",
            "telemetry",
            "feedback",
            "datasets",
            "kb_ingest",
            "analysis_lab",
            "experiments",
            "model_registry",
            "accuracy_monitoring",
            "openai",
            "jwt_auth",
            "test_runner",
            "gcp_vertex",
            "gcs_storage",
            "credit_info",
        ],
        "knowledge_base_configured": bool(s.bedrock_knowledge_base_id),
        "guardrail_configured": bool(s.bedrock_guardrail_id),
        "s3_configured": bool(s.s3_documents_bucket),
        "database_configured": s.database_configured,
        "database_ok": bool(db.get("ok")),
        "openai_configured": s.openai_configured,
        "jwt_configured": s.jwt_configured,
        "gcp_configured": s.gcp_configured,
        "vertex_ready": s.vertex_ready,
        "gcs_configured": bool(s.gcs_documents_bucket.strip()),
        "require_api_key": s.require_api_key,
    }

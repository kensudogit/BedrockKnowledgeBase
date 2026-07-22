from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.agents import invoke_agent
from src.services.analysis import analyze_image, analyze_rag, analyze_tabular, analyze_text
from src.services.bedrock_embed import embed_texts
from src.services.bedrock_image import decode_preview_data_url, generate_image
from src.services.bedrock_text import generate_text
from src.services.datasets import get_dataset, list_datasets, save_dataset
from src.services.documents import delete_document, ingest_text, list_documents
from src.services.evaluation import compare_evaluations, list_evaluations, run_model_evaluation
from src.services.experiments import get_experiment, list_experiments, log_experiment
from src.services.feedback import add_feedback, feedback_summary, list_feedback
from src.services.guardrails import apply_guardrails
from src.services.kb_ingest import get_ingestion_status, ingest_to_knowledge_base, list_ingest_jobs
from src.services.model_registry import (
    active_models,
    get_model,
    list_models,
    promote_model,
    register_model,
)
from src.services.monitoring import (
    delivery_status,
    monitor_series,
    quality_alerts,
    record_monitor_snapshot,
)
from src.services.projects import create_project, list_projects
from src.services.prompts import get_prompt, list_prompts, render_prompt, seed_default_prompts, upsert_prompt
from src.services.rag import rag_answer, retrieve_knowledge_base
from src.services.sessions import (
    append_message,
    create_session,
    get_session,
    history_for_rag,
    list_sessions,
)
from src.services.tabular import synthesize_demo_csv
from src.services.telemetry import summarize as telemetry_summary

router = APIRouter(prefix="/api", tags=["ai"])


class TextRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3
    apply_guardrail: bool = True


class ImageRequest(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1)


class GuardRequest(BaseModel):
    text: str
    source: str = "OUTPUT"


class PromptUpsert(BaseModel):
    prompt_id: Optional[str] = None
    name: str
    template: str
    use_case: str = "general"
    variables: list[str] = []


class PromptRender(BaseModel):
    values: dict[str, str]


class RagRequest(BaseModel):
    query: str
    use_case: str = "document_search"
    top_k: int = 5
    session_id: Optional[str] = None
    apply_guardrail: bool = True


class ChatRequest(BaseModel):
    message: str
    use_case: str = "document_search"
    mode: str = "rag"  # rag | text
    session_id: Optional[str] = None
    system: Optional[str] = None
    apply_guardrail: bool = True


class SessionCreate(BaseModel):
    use_case: str = "document_search"
    title: Optional[str] = None


class DocIngest(BaseModel):
    filename: str = "note.md"
    content: str
    content_type: str = "text/markdown"


class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    rating: int  # 1 or -1
    session_id: Optional[str] = None
    message_index: Optional[int] = None
    comment: str = ""
    use_case: Optional[str] = None
    model_id: Optional[str] = None
    answer_preview: str = ""
    project_id: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    client_name: str = ""
    env: str = "development"
    api_key: Optional[str] = None
    notes: str = ""


class DatasetCreate(BaseModel):
    name: str
    items: list[dict[str, Any]]
    dataset_id: Optional[str] = None
    description: str = ""
    version: str = "1.0.0"


class EvalRunRequest(BaseModel):
    name: Optional[str] = None
    dataset_id: str = "golden_default"
    project_id: Optional[str] = None
    fail_under: Optional[float] = None


class IngestKbRequest(BaseModel):
    filename: str
    content: str
    content_type: str = "text/markdown"
    project_id: Optional[str] = None


class TokenRequest(BaseModel):
    subject: str = "bkb-user"
    expires_in_sec: int = 3600


@router.post("/auth/token")
def auth_token(body: TokenRequest):
    """Issue Bearer JWT signed with Railway JWT_SECRET."""
    from src.config import get_settings
    from src.services.jwt_tokens import issue_access_token

    if not get_settings().jwt_configured:
        raise HTTPException(503, "JWT_SECRET is not configured")
    try:
        return issue_access_token(subject=body.subject, expires_in_sec=body.expires_in_sec)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)):
    """Validate Authorization: Bearer <jwt> signed with JWT_SECRET."""
    from src.config import get_settings
    from src.services.jwt_tokens import verify_access_token

    if not get_settings().jwt_configured:
        raise HTTPException(503, "JWT_SECRET is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authorization: Bearer <token> required")
    claims = verify_access_token(authorization.split(" ", 1)[1].strip())
    if not claims:
        raise HTTPException(401, "invalid or expired JWT")
    return {"ok": True, "claims": claims}


@router.post("/text/generate")
def text_generate(body: TextRequest):
    return generate_text(
        body.prompt,
        system=body.system,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        apply_guardrail=body.apply_guardrail,
    )


@router.post("/image/generate")
def image_generate(body: ImageRequest):
    out = generate_image(body.prompt, width=body.width, height=body.height)
    if not out.get("data_url"):
        out["data_url"] = decode_preview_data_url(
            out["image_base64"],
            out.get("content_type") or "image/png",
        )
    return out


@router.post("/embedding")
def embedding(body: EmbedRequest):
    return embed_texts(body.texts)


@router.post("/guardrails/apply")
def guardrails(body: GuardRequest):
    return apply_guardrails(body.text, source=body.source)


@router.get("/prompts")
def prompts_list():
    items = list_prompts()
    if not items:
        items = seed_default_prompts()
    return {"items": items}


@router.post("/prompts")
def prompts_upsert(body: PromptUpsert):
    return upsert_prompt(
        prompt_id=body.prompt_id,
        name=body.name,
        template=body.template,
        use_case=body.use_case,
        variables=body.variables,
    )


@router.post("/prompts/{prompt_id}/render")
def prompts_render(prompt_id: str, body: PromptRender):
    try:
        return render_prompt(prompt_id, body.values)
    except KeyError:
        raise HTTPException(404, "prompt not found")


@router.get("/prompts/{prompt_id}")
def prompts_get(prompt_id: str):
    p = get_prompt(prompt_id)
    if not p:
        raise HTTPException(404, "prompt not found")
    return p


@router.post("/evaluation/run")
def evaluation_run(body: Optional[EvalRunRequest] = None, name: Optional[str] = None):
    req = body or EvalRunRequest(name=name)
    try:
        return run_model_evaluation(
            name=req.name,
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            fail_under=req.fail_under,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/evaluation")
def evaluation_list():
    return {"items": list_evaluations()}


@router.get("/evaluation/compare")
def evaluation_compare(a: str, b: str):
    try:
        return compare_evaluations(a, b)
    except KeyError:
        raise HTTPException(404, "eval not found")


@router.post("/rag/query")
def rag_query(body: RagRequest):
    hist = history_for_rag(body.session_id)
    out = rag_answer(
        body.query,
        use_case=body.use_case,
        top_k=body.top_k,
        history=hist,
        apply_guardrail=body.apply_guardrail,
    )
    if body.session_id:
        append_message(body.session_id, role="user", content=body.query, use_case=body.use_case)
        append_message(
            body.session_id,
            role="assistant",
            content=out.get("answer") or "",
            citations=out.get("citations") or [],
            meta={"blocked": out.get("blocked"), "mock": out.get("mock")},
            use_case=body.use_case,
        )
        out["session_id"] = body.session_id
    return out


@router.post("/rag/retrieve")
def rag_retrieve(body: RagRequest):
    return retrieve_knowledge_base(body.query, top_k=body.top_k)


@router.post("/chat")
def chat(body: ChatRequest):
    """Multi-turn chat: creates session if needed, keeps history for RAG context."""
    sid = body.session_id or create_session(use_case=body.use_case)["session_id"]
    append_message(sid, role="user", content=body.message, use_case=body.use_case)

    if body.mode == "text":
        hist = history_for_rag(sid)
        ctx = "\n".join(f"{h['role']}: {h['content']}" for h in hist[:-1][-6:])
        prompt = f"{ctx}\nuser: {body.message}" if ctx else body.message
        gen = generate_text(
            prompt,
            system=body.system or "丁寧な日本語で回答してください。",
            apply_guardrail=body.apply_guardrail,
        )
        answer = gen.get("text") or ""
        cites: list[Any] = []
        meta = {"mode": "text", "mock": gen.get("mock")}
    else:
        hist = history_for_rag(sid)
        # exclude the user message we just appended from being duplicated in history
        hist_prior = hist[:-1] if hist and hist[-1].get("role") == "user" else hist
        out = rag_answer(
            body.message,
            use_case=body.use_case,
            history=hist_prior,
            apply_guardrail=body.apply_guardrail,
        )
        answer = out.get("answer") or ""
        cites = out.get("citations") or []
        meta = {
            "mode": "rag",
            "mock": out.get("mock"),
            "blocked": out.get("blocked"),
            "source": out.get("source"),
        }

    append_message(
        sid,
        role="assistant",
        content=answer,
        citations=cites,
        meta=meta,
        use_case=body.use_case,
    )
    sess = get_session(sid)
    return {
        "session_id": sid,
        "answer": answer,
        "citations": cites,
        "messages": (sess or {}).get("messages") or [],
        **meta,
        "use_case": body.use_case,
    }


@router.post("/sessions")
def sessions_create(body: SessionCreate):
    return create_session(use_case=body.use_case, title=body.title)


@router.get("/sessions")
def sessions_list():
    return {"items": list_sessions()}


@router.get("/sessions/{session_id}")
def sessions_get(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    return sess


@router.get("/documents")
def documents_list():
    return {"items": list_documents()}


@router.post("/documents")
def documents_create(body: DocIngest):
    if not body.content.strip():
        raise HTTPException(400, "content is empty")
    return ingest_text(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
    )


@router.post("/documents/kb-ingest")
def documents_kb_ingest(body: IngestKbRequest):
    if not body.content.strip():
        raise HTTPException(400, "content is empty")
    return ingest_to_knowledge_base(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
        project_id=body.project_id,
    )


@router.get("/documents/ingest-jobs")
def documents_ingest_jobs():
    return {"items": list_ingest_jobs()}


@router.get("/documents/ingest-jobs/{ingestion_job_id}")
def documents_ingest_status(ingestion_job_id: str):
    return get_ingestion_status(ingestion_job_id)


@router.post("/documents/upload")
async def documents_upload(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp932", errors="ignore")
    if not text.strip():
        raise HTTPException(400, "empty or unsupported file")
    name = file.filename or f"upload-{uuid4().hex[:8]}.txt"
    return ingest_text(
        filename=name,
        content=text,
        content_type=file.content_type or "text/plain",
    )


@router.delete("/documents/{document_id}")
def documents_delete(document_id: str):
    if not delete_document(document_id):
        raise HTTPException(404, "document not found")
    return {"ok": True, "document_id": document_id}


@router.post("/agents/invoke")
def agents_invoke(body: AgentRequest):
    return invoke_agent(body.message, session_id=body.session_id)


@router.get("/use-cases")
def use_cases():
    return {
        "items": [
            {"id": "internal_chatbot", "label": "社内チャットボット"},
            {"id": "faq", "label": "FAQシステム"},
            {"id": "document_search", "label": "文書検索（RAG）"},
            {"id": "contract_review", "label": "契約書レビュー"},
            {"id": "codegen", "label": "ソースコード生成"},
            {"id": "callcenter", "label": "コールセンター支援"},
            {"id": "medical_search", "label": "医療文書検索"},
            {"id": "finance_advice", "label": "金融アドバイス"},
            {"id": "ocr", "label": "OCRとの連携"},
            {"id": "ai_agent", "label": "AIエージェント"},
        ]
    }


@router.get("/projects")
def projects_list():
    return {"items": list_projects()}


@router.post("/projects")
def projects_create(body: ProjectCreate):
    return create_project(
        name=body.name,
        client_name=body.client_name,
        env=body.env,
        api_key=body.api_key,
        notes=body.notes,
    )


@router.post("/feedback")
def feedback_create(body: FeedbackRequest):
    try:
        return add_feedback(
            rating=body.rating,
            session_id=body.session_id,
            message_index=body.message_index,
            comment=body.comment,
            use_case=body.use_case,
            model_id=body.model_id,
            answer_preview=body.answer_preview,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/feedback")
def feedback_list():
    return {"items": list_feedback(), "summary": feedback_summary()}


@router.get("/datasets")
def datasets_list():
    return {"items": list_datasets()}


@router.get("/datasets/{dataset_id}")
def datasets_get(dataset_id: str):
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, "dataset not found")
    return ds


@router.post("/datasets")
def datasets_create(body: DatasetCreate):
    return save_dataset(
        name=body.name,
        items=body.items,
        dataset_id=body.dataset_id,
        description=body.description,
        version=body.version,
    )


@router.get("/metrics/summary")
def metrics_summary():
    return telemetry_summary()


@router.get("/ops/summary")
def ops_summary():
    from src.config import get_settings

    s = get_settings()
    return {
        "app_env": s.app_env,
        "mock_mode": s.mock_mode,
        "telemetry": telemetry_summary(),
        "feedback": feedback_summary(),
        "projects": list_projects(),
        "datasets": list_datasets(),
        "ingest_jobs": list_ingest_jobs(10),
        "recent_evals": list_evaluations(5),
        "delivery": delivery_status(),
        "models": list_models()[:20],
        "experiments": list_experiments(10),
        "monitor": quality_alerts(),
    }


class TestRunRequest(BaseModel):
    suites: list[str] = Field(default_factory=lambda: ["python", "frontend"])


@router.post("/tests/run")
def tests_run(body: TestRunRequest):
    """Start pytest + vitest in background; poll GET /api/tests/runs/{id}."""
    from src.services.test_runner import start_tests_async

    try:
        return start_tests_async(body.suites)
    except Exception as exc:
        raise HTTPException(500, f"test runner failed: {exc}") from exc


@router.get("/tests/latest")
def tests_latest():
    from src.services.test_runner import latest_run

    run = latest_run()
    if not run:
        return {"run": None}
    return {"run": run}


@router.get("/tests/history")
def tests_history(limit: int = 20):
    from src.services.test_runner import list_runs

    return {"items": list_runs(limit=min(max(limit, 1), 50))}


@router.get("/tests/runs/{run_id}")
def tests_get_run(run_id: str):
    from src.services.test_runner import get_run

    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "test run not found")
    return run


class AnalysisTextRequest(BaseModel):
    prompt: str
    project_id: Optional[str] = None


class AnalysisRagRequest(BaseModel):
    query: str
    use_case: str = "document_search"
    project_id: Optional[str] = None


class AnalysisTabularRequest(BaseModel):
    csv_text: str
    target: Optional[str] = None
    task: str = "auto"
    project_id: Optional[str] = None


class ExperimentCreate(BaseModel):
    name: str
    modality: str
    params: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    artifacts: dict[str, Any] = {}
    project_id: Optional[str] = None
    notes: str = ""


class ModelRegister(BaseModel):
    name: str
    modality: str
    version: str = "0.1.0"
    provider: str = "bedrock"
    model_uri: str = ""
    metrics: dict[str, Any] = {}
    experiment_id: Optional[str] = None
    project_id: Optional[str] = None
    stage: str = "development"
    meta: dict[str, Any] = {}


class ModelPromote(BaseModel):
    to_stage: str


@router.post("/analysis/text")
def analysis_text(body: AnalysisTextRequest):
    return analyze_text(body.prompt, project_id=body.project_id)


@router.post("/analysis/image")
def analysis_image(body: AnalysisTextRequest):
    out = analyze_image(body.prompt, project_id=body.project_id)
    if out.get("result"):
        out["result"]["data_url"] = decode_preview_data_url(out["result"].get("image_base64") or "")
    return out


@router.post("/analysis/rag")
def analysis_rag(body: AnalysisRagRequest):
    return analyze_rag(body.query, use_case=body.use_case, project_id=body.project_id)


@router.post("/analysis/tabular")
def analysis_tabular(body: AnalysisTabularRequest):
    try:
        return analyze_tabular(
            body.csv_text,
            target=body.target,
            task=body.task,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/analysis/tabular/demo-csv")
def analysis_tabular_demo():
    return {"csv_text": synthesize_demo_csv(), "target": "churn"}


@router.get("/experiments")
def experiments_list(modality: Optional[str] = None):
    return {"items": list_experiments(50, modality=modality)}


@router.get("/experiments/{experiment_id}")
def experiments_get(experiment_id: str):
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(404, "experiment not found")
    return exp


@router.post("/experiments")
def experiments_create(body: ExperimentCreate):
    return log_experiment(
        name=body.name,
        modality=body.modality,
        params=body.params,
        metrics=body.metrics,
        artifacts=body.artifacts,
        project_id=body.project_id,
        notes=body.notes,
    )


@router.get("/models")
def models_list(stage: Optional[str] = None):
    return {"items": list_models(stage=stage), "active": active_models()}


@router.get("/models/{model_id}")
def models_get(model_id: str):
    m = get_model(model_id)
    if not m:
        raise HTTPException(404, "model not found")
    return m


@router.post("/models")
def models_register(body: ModelRegister):
    try:
        return register_model(
            name=body.name,
            modality=body.modality,
            version=body.version,
            provider=body.provider,
            model_uri=body.model_uri,
            metrics=body.metrics,
            experiment_id=body.experiment_id,
            project_id=body.project_id,
            stage=body.stage,
            meta=body.meta,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/models/{model_id}/promote")
def models_promote(model_id: str, body: ModelPromote):
    try:
        return promote_model(model_id, body.to_stage)
    except KeyError:
        raise HTTPException(404, "model not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/monitoring/series")
def monitoring_series():
    return {"items": monitor_series()}


@router.post("/monitoring/snapshot")
def monitoring_snapshot():
    return record_monitor_snapshot(source="api")


@router.get("/monitoring/alerts")
def monitoring_alerts():
    return quality_alerts()


@router.get("/delivery/status")
def delivery_status_api():
    return delivery_status()


# --- GCP / Vertex / GCS ---


class GcpTextRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3
    apply_guardrail: bool = True


class GcsUploadRequest(BaseModel):
    filename: str
    content: str
    content_type: str = "text/plain"
    project_id: Optional[str] = None


@router.get("/gcp/status")
def gcp_status_api():
    from src.gcp_clients import gcp_status

    return gcp_status()


@router.post("/gcp/text")
def gcp_text_generate(body: GcpTextRequest):
    from src.services.vertex_text import generate_text_vertex

    try:
        out = generate_text_vertex(
            body.prompt,
            system=body.system,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    if body.apply_guardrail:
        from src.config import get_settings
        from src.services.guardrails import apply_guardrails

        if get_settings().enable_guardrails:
            gr = apply_guardrails(out["text"])
            out["guardrail"] = gr
            if gr.get("action") == "GUARDRAIL_INTERVENED":
                out["text"] = gr["outputs"][0]["text"]
    return out


@router.post("/gcp/storage/upload")
def gcp_storage_upload(body: GcsUploadRequest):
    from src.services.gcs_storage import upload_document

    return upload_document(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
        project_id=body.project_id,
    )


@router.get("/gcp/storage/uploads")
def gcp_storage_list():
    from src.services.gcs_storage import list_uploads

    return {"items": list_uploads()}


# --- 信用情報管理 ---


class CreditSubjectCreate(BaseModel):
    full_name: str
    birth_date: str
    phone: str = ""
    email: str = ""
    external_ref: str = ""
    notes: str = ""


class CreditContractCreate(BaseModel):
    contract_type: str = "credit_card"
    lender: str
    credit_limit: int = 0
    balance: int = 0
    status: str = "open"
    opened_on: str = ""
    payment_status: str = "current"
    months_delinquent: int = 0


class CreditConsentCreate(BaseModel):
    purpose: str = "credit_inquiry"
    requester: str
    channel: str = "web"
    expires_at: str = ""


class CreditInquiryCreate(BaseModel):
    requester: str
    purpose: str = "credit_review"
    inquiry_type: str = "hard"
    require_consent: bool = True


@router.get("/credit/subjects")
def credit_subjects_list():
    from src.services.credit_info import list_subjects

    return {"items": list_subjects()}


@router.post("/credit/subjects")
def credit_subjects_create(body: CreditSubjectCreate):
    from src.services.credit_info import register_subject

    return register_subject(
        full_name=body.full_name,
        birth_date=body.birth_date,
        phone=body.phone,
        email=body.email,
        external_ref=body.external_ref,
        notes=body.notes,
    )


@router.get("/credit/subjects/{subject_id}")
def credit_subjects_get(subject_id: str, reveal: bool = False):
    from src.services.credit_info import get_subject

    item = get_subject(subject_id, reveal=reveal)
    if not item:
        raise HTTPException(404, "subject not found")
    return item


@router.post("/credit/subjects/{subject_id}/contracts")
def credit_contracts_add(subject_id: str, body: CreditContractCreate):
    from src.services.credit_info import add_contract

    try:
        return add_contract(
            subject_id=subject_id,
            contract_type=body.contract_type,
            lender=body.lender,
            credit_limit=body.credit_limit,
            balance=body.balance,
            status=body.status,
            opened_on=body.opened_on,
            payment_status=body.payment_status,
            months_delinquent=body.months_delinquent,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/contracts")
def credit_contracts_list(subject_id: str):
    from src.services.credit_info import get_subject, list_contracts

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_contracts(subject_id)}


@router.post("/credit/subjects/{subject_id}/consents")
def credit_consents_add(subject_id: str, body: CreditConsentCreate):
    from src.services.credit_info import record_consent

    try:
        return record_consent(
            subject_id=subject_id,
            purpose=body.purpose,
            requester=body.requester,
            channel=body.channel,
            expires_at=body.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/consents")
def credit_consents_list(subject_id: str):
    from src.services.credit_info import get_subject, list_consents

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_consents(subject_id)}


@router.post("/credit/subjects/{subject_id}/inquiries")
def credit_inquiries_add(subject_id: str, body: CreditInquiryCreate):
    from src.services.credit_info import record_inquiry

    try:
        return record_inquiry(
            subject_id=subject_id,
            requester=body.requester,
            purpose=body.purpose,
            inquiry_type=body.inquiry_type,
            require_consent=body.require_consent,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/inquiries")
def credit_inquiries_list(subject_id: str):
    from src.services.credit_info import get_subject, list_inquiries

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_inquiries(subject_id)}


@router.get("/credit/subjects/{subject_id}/score")
def credit_score_get(subject_id: str):
    from src.services.credit_info import compute_score, get_subject

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return compute_score(subject_id)


@router.get("/credit/subjects/{subject_id}/report")
def credit_report_get(subject_id: str, reveal: bool = False):
    from src.services.credit_info import build_report

    try:
        return build_report(subject_id, reveal=reveal)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/audit")
def credit_audit_list(limit: int = 100, subject_id: Optional[str] = None):
    from src.services.credit_info import list_audit

    return {"items": list_audit(limit=limit, subject_id=subject_id)}


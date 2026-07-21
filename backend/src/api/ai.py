from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.agents import invoke_agent
from src.services.bedrock_embed import embed_texts
from src.services.bedrock_image import decode_preview_data_url, generate_image
from src.services.bedrock_text import generate_text
from src.services.documents import delete_document, ingest_text, list_documents
from src.services.evaluation import list_evaluations, run_model_evaluation
from src.services.guardrails import apply_guardrails
from src.services.prompts import get_prompt, list_prompts, render_prompt, seed_default_prompts, upsert_prompt
from src.services.rag import rag_answer, retrieve_knowledge_base
from src.services.sessions import (
    append_message,
    create_session,
    get_session,
    history_for_rag,
    list_sessions,
)

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
    out["data_url"] = decode_preview_data_url(out["image_base64"])
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
def evaluation_run(name: Optional[str] = None):
    return run_model_evaluation(name=name)


@router.get("/evaluation")
def evaluation_list():
    return {"items": list_evaluations()}


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

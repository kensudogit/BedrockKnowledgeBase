from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.services.bedrock_embed import embed_texts
from src.services.bedrock_text import generate_text
from src.services.mock_ai import mock_rag

def _samples_dir() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[3] / "samples",  # repo root (local)
        here.parents[2] / "samples",  # backend/samples
        Path("/app/samples"),  # docker mount
        Path.cwd() / "samples",
        Path.cwd().parent / "samples",
    ):
        if candidate.exists():
            return candidate
    return here.parents[3] / "samples"


def _load_local_chunks(limit: int = 40) -> list[str]:
    chunks: list[str] = []
    samples = _samples_dir()
    if not samples.exists():
        return ["デモ文書がありません。samples/ に Markdown を配置してください。"]
    for path in sorted(samples.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i in range(0, len(text), 500):
            piece = text[i : i + 500].strip()
            if piece:
                chunks.append(f"[{path.name}] {piece}")
            if len(chunks) >= limit:
                return chunks
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def retrieve_local(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    chunks = _load_local_chunks()
    emb = embed_texts([query, *chunks])
    vectors = emb["embeddings"]
    if len(vectors) < 2:
        return [{"text": c, "score": 0.5} for c in chunks[:top_k]]
    q = vectors[0]
    scored = []
    for i, c in enumerate(chunks):
        scored.append({"text": c, "score": round(_cosine(q, vectors[i + 1]), 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def retrieve_knowledge_base(query: str, top_k: int = 4) -> dict[str, Any]:
    settings = get_settings()
    if settings.mock_mode or not settings.bedrock_knowledge_base_id:
        cites = retrieve_local(query, top_k=top_k)
        return {"citations": cites, "source": "local_samples", "mock": True}

    from src.aws_clients import bedrock_agent_runtime

    resp = bedrock_agent_runtime().retrieve(
        knowledgeBaseId=settings.bedrock_knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": top_k}
        },
    )
    cites = []
    for r in resp.get("retrievalResults", []):
        cites.append(
            {
                "text": (r.get("content") or {}).get("text", ""),
                "score": r.get("score"),
                "location": r.get("location"),
            }
        )
    return {"citations": cites, "source": "bedrock_kb", "mock": False, "raw": resp}


def rag_answer(query: str, *, use_case: str = "document_search") -> dict[str, Any]:
    settings = get_settings()
    retrieved = retrieve_knowledge_base(query)
    cites = retrieved.get("citations") or []
    context = "\n\n".join(c.get("text", "") for c in cites)

    if settings.mock_mode:
        out = mock_rag(query, [c.get("text", "") for c in cites])
        out["retrieval"] = retrieved
        out["use_case"] = use_case
        return out

    # Prefer RetrieveAndGenerate when KB configured
    if settings.bedrock_knowledge_base_id:
        from src.aws_clients import bedrock_agent_runtime

        resp = bedrock_agent_runtime().retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": settings.bedrock_knowledge_base_id,
                    "modelArn": f"arn:aws:bedrock:{settings.aws_region}::foundation-model/{settings.bedrock_text_model_id}",
                },
            },
        )
        return {
            "answer": (resp.get("output") or {}).get("text", ""),
            "citations": resp.get("citations", []),
            "retrieval": retrieved,
            "mock": False,
            "use_case": use_case,
        }

    gen = generate_text(
        f"次の根拠のみで日本語回答してください。\n根拠:\n{context}\n\n質問: {query}",
        system="あなたは社内文書検索アシスタントです。根拠外は推測しないでください。",
    )
    return {
        "answer": gen["text"],
        "citations": cites,
        "retrieval": retrieved,
        "mock": gen.get("mock", False),
        "use_case": use_case,
    }

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.aws_clients import dynamodb_resource
from src.config import get_settings
from src.services.rag import rag_answer

_MEM: list[dict[str, Any]] = []

GOLDEN = [
    {
        "id": "g1",
        "prompt": "有給休暇の申請手順を教えて",
        "expected_keywords": ["申請", "勤怠", "承認"],
        "expected_sources": ["有給", "休暇", "faq", "hr", "人事"],
        "use_case": "faq",
    },
    {
        "id": "g2",
        "prompt": "情報セキュリティの基本方針の要点は？",
        "expected_keywords": ["機密", "アクセス", "セキュリティ"],
        "expected_sources": ["セキュリティ", "security", "情報"],
        "use_case": "document_search",
    },
    {
        "id": "g3",
        "prompt": "契約書の秘密保持で確認すべき点は？",
        "expected_keywords": ["秘密", "期間", "例外"],
        "expected_sources": ["契約", "秘密", "nda", "contract"],
        "use_case": "contract_review",
    },
]


def _score_keywords(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hit = sum(1 for k in keywords if k in answer)
    return round(hit / len(keywords), 3)


def _score_retrieval(citations: list[dict[str, Any]], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0 if citations else 0.0
    blob = " ".join(
        f"{c.get('source', '')} {c.get('text', '')}" for c in citations
    ).lower()
    hit = sum(1 for s in expected_sources if s.lower() in blob)
    return round(hit / len(expected_sources), 3)


def run_model_evaluation(name: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    samples = []
    kw_scores = []
    ret_scores = []
    for g in GOLDEN:
        out = rag_answer(
            g["prompt"],
            use_case=g.get("use_case", "document_search"),
            apply_guardrail=False,
        )
        answer = out.get("answer") or ""
        cites = out.get("citations") or []
        kw = _score_keywords(answer, g["expected_keywords"])
        ret = _score_retrieval(cites, g.get("expected_sources") or [])
        combined = round(0.55 * kw + 0.45 * ret, 3)
        kw_scores.append(kw)
        ret_scores.append(ret)
        samples.append(
            {
                "id": g["id"],
                "prompt": g["prompt"],
                "answer": answer[:500],
                "keyword_score": kw,
                "retrieval_score": ret,
                "combined_score": combined,
                "citation_count": len(cites),
                "sources": [c.get("source") for c in cites[:4]],
                "mock": out.get("mock", False),
            }
        )

    n = len(samples) or 1
    metrics = {
        "avg_keyword_score": round(sum(kw_scores) / n, 3),
        "avg_retrieval_score": round(sum(ret_scores) / n, 3),
        "avg_combined_score": round(
            sum(s["combined_score"] for s in samples) / n,
            3,
        ),
        "n_samples": len(samples),
        "mode": "rag",
        "model_id": settings.bedrock_text_model_id if not settings.mock_mode else "local-rag",
    }
    run = {
        "eval_id": str(uuid4()),
        "name": name or f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "model_id": metrics["model_id"],
        "metrics": metrics,
        "samples": samples,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        table = dynamodb_resource().Table(settings.dynamodb_table_evals)
        table.put_item(Item=run)
    except Exception:
        _MEM.insert(0, run)
    return run


def list_evaluations(limit: int = 20) -> list[dict[str, Any]]:
    settings = get_settings()
    try:
        resp = dynamodb_resource().Table(settings.dynamodb_table_evals).scan(Limit=limit)
        items = resp.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]
    except Exception:
        return _MEM[:limit]

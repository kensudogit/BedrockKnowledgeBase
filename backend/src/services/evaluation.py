from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services.bedrock_text import generate_text
from src.aws_clients import dynamodb_resource
from src.config import get_settings

_MEM: list[dict[str, Any]] = []

GOLDEN = [
    {
        "id": "g1",
        "prompt": "有給休暇の申請手順を一言で教えて",
        "expected_keywords": ["申請", "勤怠", "承認"],
    },
    {
        "id": "g2",
        "prompt": "情報セキュリティの基本方針の要点は？",
        "expected_keywords": ["機密", "アクセス", "セキュリティ"],
    },
    {
        "id": "g3",
        "prompt": "契約書の秘密保持条項で確認すべき点は？",
        "expected_keywords": ["秘密", "期間", "例外"],
    },
]


def _score(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hit = sum(1 for k in keywords if k in answer)
    return round(hit / len(keywords), 3)


def run_model_evaluation(name: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    samples = []
    scores = []
    for g in GOLDEN:
        out = generate_text(g["prompt"], system="簡潔に日本語で回答してください。", apply_guardrail=False)
        s = _score(out["text"], g["expected_keywords"])
        scores.append(s)
        samples.append(
            {
                "id": g["id"],
                "prompt": g["prompt"],
                "answer": out["text"][:500],
                "keyword_score": s,
                "mock": out.get("mock", False),
            }
        )

    metrics = {
        "avg_keyword_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "n_samples": len(scores),
        "model_id": settings.bedrock_text_model_id if not settings.mock_mode else "mock-text",
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

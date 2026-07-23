"""RAG モデル評価 — ゴールデンデータセットによるキーワード・検索スコア計測。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.aws_clients import dynamodb_resource
from src.config import get_settings
from src.services import persist
from src.services.datasets import get_dataset
from src.services.rag import rag_answer

_MEM: list[dict[str, Any]] = []


def _score_keywords(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hit = sum(1 for k in keywords if k in answer)
    return round(hit / len(keywords), 3)


def _score_retrieval(citations: list[dict[str, Any]], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0 if citations else 0.0
    blob = " ".join(f"{c.get('source', '')} {c.get('text', '')}" for c in citations).lower()
    hit = sum(1 for s in expected_sources if s.lower() in blob)
    return round(hit / len(expected_sources), 3)


def run_model_evaluation(
    name: str | None = None,
    *,
    dataset_id: str = "golden_default",
    project_id: str | None = None,
    fail_under: float | None = None,
) -> dict[str, Any]:
    """
    データセット各サンプルに対して RAG を実行し、スコアを集計する。
    fail_under 指定時は合格/不合格を metrics に含める。
    """
    settings = get_settings()
    ds = get_dataset(dataset_id)
    if not ds or not ds.get("items"):
        raise ValueError(f"dataset not found or empty: {dataset_id}")

    samples = []
    kw_scores = []
    ret_scores = []
    for g in ds["items"]:
        out = rag_answer(
            g["prompt"],
            use_case=g.get("use_case", "document_search"),
            apply_guardrail=False,
        )
        answer = out.get("answer") or ""
        cites = out.get("citations") or []
        kw = _score_keywords(answer, g.get("expected_keywords") or [])
        ret = _score_retrieval(cites, g.get("expected_sources") or [])
        combined = round(0.55 * kw + 0.45 * ret, 3)
        kw_scores.append(kw)
        ret_scores.append(ret)
        samples.append(
            {
                "id": g.get("id"),
                "prompt": g.get("prompt"),
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
        "avg_combined_score": round(sum(s["combined_score"] for s in samples) / n, 3),
        "n_samples": len(samples),
        "mode": "rag",
        "dataset_id": dataset_id,
        "dataset_version": ds.get("version"),
        "model_id": settings.bedrock_text_model_id if not settings.mock_mode else "local-rag",
        "app_env": settings.app_env,
    }
    if fail_under is not None:
        metrics["fail_under"] = fail_under
        metrics["passed"] = metrics["avg_combined_score"] >= fail_under

    run = {
        "eval_id": str(uuid4()),
        "project_id": project_id,
        "name": name or f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "dataset_id": dataset_id,
        "model_id": metrics["model_id"],
        "metrics": metrics,
        "samples": samples,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    persist.append("eval_runs", run)
    try:
        table = dynamodb_resource().Table(settings.dynamodb_table_evals)
        table.put_item(Item=run)
    except Exception:
        _MEM.insert(0, run)
    return run


def list_evaluations(limit: int = 20) -> list[dict[str, Any]]:
    """評価実行履歴をファイル・DynamoDB・メモリからマージして返す。"""
    settings = get_settings()
    file_items = persist.load("eval_runs")
    try:
        resp = dynamodb_resource().Table(settings.dynamodb_table_evals).scan(Limit=limit)
        items = resp.get("Items", [])
    except Exception:
        items = list(_MEM)
    merged = {i.get("eval_id"): i for i in file_items + items if i.get("eval_id")}
    out = list(merged.values())
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out[:limit]


def compare_evaluations(eval_a: str, eval_b: str) -> dict[str, Any]:
    """2 件の評価結果のメトリクス差分（B − A）を返す。"""
    runs = {r.get("eval_id"): r for r in list_evaluations(100)}
    a = runs.get(eval_a)
    b = runs.get(eval_b)
    if not a or not b:
        raise KeyError("eval not found")
    ma = a.get("metrics") or {}
    mb = b.get("metrics") or {}
    keys = ("avg_combined_score", "avg_keyword_score", "avg_retrieval_score")
    delta = {k: round(float(mb.get(k) or 0) - float(ma.get(k) or 0), 3) for k in keys}
    return {"a": a.get("eval_id"), "b": b.get("eval_id"), "delta_b_minus_a": delta, "a_metrics": ma, "b_metrics": mb}

"""生成/自然言語/画像/表形式などモダリティ別の統合分析エントリ。"""
from __future__ import annotations

from typing import Any

from src.services.bedrock_embed import embed_texts
from src.services.bedrock_image import generate_image
from src.services.bedrock_text import generate_text
from src.services.experiments import log_experiment
from src.services.rag import rag_answer
from src.services.tabular import correlate_numeric, profile_tabular, train_tabular_baseline


def analyze_text(prompt: str, *, project_id: str | None = None) -> dict[str, Any]:
    """テキスト生成・埋め込みを実行し、実験ログを記録する。"""
    out = generate_text(prompt, system="分析結果を箇条書きで簡潔に日本語でまとめてください。")
    emb = embed_texts([prompt])
    exp = log_experiment(
        name="text-analysis",
        modality="text",
        params={"prompt_len": len(prompt)},
        metrics={
            "output_chars": len(out.get("text") or ""),
            "embed_dim": emb.get("dimensions"),
            "mock": out.get("mock"),
        },
        artifacts={"preview": (out.get("text") or "")[:240]},
        project_id=project_id,
    )
    return {"modality": "text", "result": out, "embedding": emb, "experiment": exp}


def analyze_image(prompt: str, *, project_id: str | None = None) -> dict[str, Any]:
    """画像生成を実行し、実験ログを記録する。"""
    out = generate_image(prompt)
    exp = log_experiment(
        name="image-generation",
        modality="image",
        params={"prompt": prompt[:200]},
        metrics={"mock": out.get("mock")},
        artifacts={"content_type": out.get("content_type")},
        project_id=project_id,
    )
    return {"modality": "image", "result": out, "experiment": exp}


def analyze_rag(query: str, *, use_case: str = "document_search", project_id: str | None = None) -> dict[str, Any]:
    """RAG 検索・回答を実行し、実験ログを記録する。"""
    out = rag_answer(query, use_case=use_case)
    exp = log_experiment(
        name="rag-analysis",
        modality="rag",
        params={"use_case": use_case, "query_len": len(query)},
        metrics={
            "citation_count": len(out.get("citations") or []),
            "blocked": out.get("blocked"),
            "mock": out.get("mock"),
        },
        artifacts={"answer_preview": (out.get("answer") or "")[:240]},
        project_id=project_id,
    )
    return {"modality": "rag", "result": out, "experiment": exp}


def analyze_tabular(
    csv_text: str,
    *,
    target: str | None = None,
    task: str = "auto",
    project_id: str | None = None,
) -> dict[str, Any]:
    """表形式データのプロファイル・相関・ベースライン学習を実行する。"""
    profile = profile_tabular(csv_text)
    corr = None
    try:
        corr = correlate_numeric(csv_text)
    except Exception:
        corr = None
    train = None
    if target:
        train = train_tabular_baseline(csv_text, target=target, task=task)
    metrics = {"n_rows": profile.get("n_rows"), "n_columns": profile.get("n_columns")}
    if train:
        metrics.update(train.get("metrics") or {})
    exp = log_experiment(
        name="tabular-analysis",
        modality="tabular",
        params={"target": target, "task": task},
        metrics=metrics,
        artifacts={"features": (train or {}).get("features") or []},
        project_id=project_id,
    )
    return {
        "modality": "tabular",
        "profile": profile,
        "correlation": corr,
        "train": train,
        "experiment": exp,
    }

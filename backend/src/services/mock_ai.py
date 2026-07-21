"""Local mock implementations when Bedrock credentials / KB are unavailable."""
from __future__ import annotations

import base64
import hashlib
import math
import struct
from typing import Any


def mock_text(prompt: str, system: str | None = None) -> dict[str, Any]:
    preface = (system + "\n") if system else ""
    body = (
        f"{preface}【モック応答】Bedrock 未接続のためローカル生成です。\n"
        f"入力要約: {prompt[:280]}{'…' if len(prompt) > 280 else ''}\n\n"
        "推奨次アクション:\n"
        "1. AWS 認証情報と Knowledge Base ID を設定\n"
        "2. USE_BEDROCK_MOCK=false で本番モデルへ切替\n"
        "3. S3 に文書を配置し Knowledge Bases 同期"
    )
    return {
        "text": body,
        "model": "mock-text",
        "mock": True,
        "usage": {"input_tokens": len(prompt) // 4, "output_tokens": len(body) // 4},
    }


def mock_image(prompt: str) -> dict[str, Any]:
    # 1x1 PNG
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    return {
        "image_base64": base64.b64encode(png).decode("ascii"),
        "content_type": "image/png",
        "prompt": prompt,
        "model": "mock-image",
        "mock": True,
    }


def mock_embed(texts: list[str], dim: int = 64) -> dict[str, Any]:
    vectors = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        vals = []
        for i in range(dim):
            # deterministic pseudo-embedding
            b = h[i % len(h)]
            vals.append((b / 255.0) * 2 - 1)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        vectors.append([round(v / norm, 6) for v in vals])
    return {"embeddings": vectors, "dimensions": dim, "model": "mock-embed", "mock": True}


def mock_guardrail(text: str) -> dict[str, Any]:
    blocked_words = ["爆弾の作り方", "クレジットカード番号を全部教えて"]
    intervened = any(w in text for w in blocked_words)
    return {
        "action": "GUARDRAIL_INTERVENED" if intervened else "NONE",
        "outputs": [{"text": "[ブロックされました]" if intervened else text}],
        "assessments": [{"topicPolicy": {"blocked": intervened}}],
        "mock": True,
    }


def mock_rag(query: str, contexts: list[str]) -> dict[str, Any]:
    cites = contexts[:3]
    answer = (
        f"【RAGモック】クエリ「{query}」に対し、ローカル文書チャンク "
        f"{len(cites)} 件を根拠に回答します。\n\n"
        + "\n---\n".join(c[:200] for c in cites)
        + ("\n\n（出典は samples/ 配下のデモ文書です）" if cites else "\n関連文書が見つかりませんでした。")
    )
    return {
        "answer": answer,
        "citations": [{"text": c[:240], "score": round(0.9 - i * 0.1, 2)} for i, c in enumerate(cites)],
        "mock": True,
    }


def pack_f32(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)

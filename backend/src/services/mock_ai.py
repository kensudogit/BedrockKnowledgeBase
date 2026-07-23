"""Bedrock 未接続時に使うローカルモック実装（テキスト・画像・埋め込み・RAG 等）。"""
from __future__ import annotations

import base64
import hashlib
import math
import struct
from typing import Any


def mock_text(prompt: str, system: str | None = None) -> dict[str, Any]:
    """テキスト生成のモック応答を返す。"""
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
    """UI で見える SVG プレースホルダ画像を返す（1x1 PNG は失敗に見えやすい）。"""
    safe = (
        prompt.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    line1 = safe[:42]
    line2 = safe[42:84]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f2744"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#g)"/>
  <rect x="28" y="28" width="456" height="456" rx="24" fill="none" stroke="#7dd3fc" stroke-width="2" opacity="0.55"/>
  <text x="256" y="170" text-anchor="middle" fill="#e0f2fe" font-size="34" font-family="Segoe UI, sans-serif" font-weight="700">MOCK IMAGE</text>
  <text x="256" y="220" text-anchor="middle" fill="#bae6fd" font-size="16" font-family="Segoe UI, sans-serif">Bedrock 未接続 — プレースホルダ</text>
  <text x="256" y="290" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">{line1}</text>
  <text x="256" y="322" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">{line2}</text>
  <text x="256" y="400" text-anchor="middle" fill="#93c5fd" font-size="14" font-family="Segoe UI, sans-serif">USE_BEDROCK_MOCK=false で Titan Image へ</text>
</svg>"""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {
        "image_base64": b64,
        "content_type": "image/svg+xml",
        "prompt": prompt,
        "model": "mock-image",
        "mock": True,
        "data_url": f"data:image/svg+xml;base64,{b64}",
    }


def mock_embed(texts: list[str], dim: int = 64) -> dict[str, Any]:
    """文字 n-gram ハッシュによる疑似埋め込み（文字列全体 SHA より類似度が安定）。"""
    vectors = []
    for t in texts:
        vals = [0.0] * dim
        s = t.lower()
        # unigram + bigram + trigram
        grams = list(s) + [s[i : i + 2] for i in range(len(s) - 1)] + [s[i : i + 3] for i in range(len(s) - 2)]
        for g in grams[:800]:
            h = hashlib.md5(g.encode("utf-8")).digest()
            idx = h[0] % dim
            sign = 1.0 if h[1] % 2 == 0 else -1.0
            vals[idx] += sign
        # 全体ハッシュのバイアスで安定化
        wh = hashlib.sha256(s.encode("utf-8")).digest()
        for i in range(dim):
            vals[i] += ((wh[i % len(wh)] / 255.0) * 2 - 1) * 0.15
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        vectors.append([round(v / norm, 6) for v in vals])
    return {"embeddings": vectors, "dimensions": dim, "model": "mock-embed-ngram", "mock": True}


def mock_guardrail(text: str) -> dict[str, Any]:
    """ガードレール判定のモック（禁止語で介入をシミュレート）。"""
    blocked_words = ["爆弾の作り方", "クレジットカード番号を全部教えて"]
    intervened = any(w in text for w in blocked_words)
    return {
        "action": "GUARDRAIL_INTERVENED" if intervened else "NONE",
        "outputs": [{"text": "[ブロックされました]" if intervened else text}],
        "assessments": [{"topicPolicy": {"blocked": intervened}}],
        "mock": True,
    }


def mock_rag(query: str, contexts: list[str]) -> dict[str, Any]:
    """ローカル文書チャンクを根拠にした RAG 回答のモック。"""
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
    """float ベクトルをバイナリ（struct pack）に変換する。"""
    return struct.pack(f"{len(vec)}f", *vec)

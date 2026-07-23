"""RAG 検索・回答（ローカル BM25+埋め込み / Bedrock Knowledge Base）。"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.services.bedrock_embed import embed_texts
from src.services.bedrock_text import generate_text
from src.services.guardrails import apply_guardrails
from src.services.prompts import list_prompts

_CHUNK_SIZE = 420
_CHUNK_OVERLAP = 80
_MAX_CHUNKS = 120

USE_CASE_SYSTEM: dict[str, str] = {
    "internal_chatbot": "あなたは社内アシスタントです。根拠文書に基づき丁寧な日本語で回答し、不明点は推測せず確認を促してください。",
    "faq": "あなたはFAQ担当です。手順を番号付きで簡潔に示し、根拠の文書名に触れてください。",
    "document_search": "あなたは文書検索アシスタントです。根拠のみで回答し、根拠外は『文書に記載がありません』と述べてください。",
    "contract_review": "あなたは契約書レビュー支援です。リスク・義務・例外を箇条書きで指摘し、法的助言ではない旨を添えてください。",
    "codegen": "あなたはシニアエンジニアです。根拠や要件に沿ったコードと注意点を提示してください。",
    "callcenter": "あなたはコールセンター支援です。顧客向けに共感→回答→次アクションの順で短く案内してください。",
    "medical_search": "あなたは医療文書検索支援です。一般情報として根拠を示し、診断・処方は行わないでください。",
    "finance_advice": "あなたは金融リテラシー支援です。一般情報として回答し、投資助言ではない旨を明記してください。",
    "ocr": "あなたはOCR連携アシスタントです。抽出テキストの要点整理と不足項目の確認を行ってください。",
    "ai_agent": "あなたは業務エージェントです。目的達成のための手順を計画→実行結果の形で示してください。",
}


def _samples_dir() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[3] / "samples",
        here.parents[2] / "samples",
        Path("/app/samples"),
        Path.cwd() / "samples",
        Path.cwd().parent / "samples",
    ):
        if candidate.exists():
            return candidate
    return here.parents[3] / "samples"


def uploads_dir() -> Path:
    """アップロード文書の保存ディレクトリを返す（存在しなければ作成）。"""
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[3] / "data" / "uploads",
        here.parents[2] / "data" / "uploads",
        Path("/app/data/uploads"),
        Path.cwd() / "data" / "uploads",
    ):
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    p = here.parents[3] / "data" / "uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", text.lower()) if len(t) >= 2]


def _bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    q_terms = _tokenize(query)
    if not q_terms or not docs:
        return [0.0] * len(docs)
    tokenized = [_tokenize(d) for d in docs]
    N = len(docs)
    avgdl = sum(len(t) for t in tokenized) / N
    df: dict[str, int] = {}
    for terms in tokenized:
        for term in set(terms):
            df[term] = df.get(term, 0) + 1
    scores = []
    for terms in tokenized:
        tf: dict[str, int] = {}
        for t in terms:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        dl = len(terms) or 1
        for term in q_terms:
            if term not in tf:
                continue
            n = df.get(term, 0)
            idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
            freq = tf[term]
            score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append(score)
    return scores


def _chunk_text(text: str, source: str) -> list[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    out: list[dict[str, Any]] = []
    step = max(1, _CHUNK_SIZE - _CHUNK_OVERLAP)
    idx = 0
    for start in range(0, len(text), step):
        piece = text[start : start + _CHUNK_SIZE].strip()
        if not piece:
            continue
        out.append(
            {
                "text": piece,
                "source": source,
                "chunk_index": idx,
            }
        )
        idx += 1
        if len(out) >= _MAX_CHUNKS:
            break
    return out


_INDEX_EPOCH = 0


def invalidate_local_index() -> None:
    """ローカルチャンク索引のキャッシュを無効化する。"""
    global _INDEX_EPOCH
    _INDEX_EPOCH += 1
    _load_local_chunk_records.cache_clear()


@lru_cache(maxsize=8)
def _load_local_chunk_records(epoch: int = 0) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    roots = [_samples_dir(), uploads_dir()]
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".text"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            records.extend(_chunk_text(text, path.name))
            if len(records) >= _MAX_CHUNKS:
                return tuple(records)
    if not records:
        return (
            {
                "text": "デモ文書がありません。samples/ または文書アップロードを利用してください。",
                "source": "system",
                "chunk_index": 0,
            },
        )
    return tuple(records)


def _normalize_citation(raw: dict[str, Any], *, rank: int = 0) -> dict[str, Any]:
    text = (raw.get("text") or raw.get("content") or "").strip()
    source = raw.get("source") or raw.get("filename") or ""
    if not source and text.startswith("[") and "]" in text[:80]:
        source = text[1 : text.index("]")]
        text = text[text.index("]") + 1 :].strip()
    loc = raw.get("location") or {}
    if not source and isinstance(loc, dict):
        s3 = (loc.get("s3Location") or {}).get("uri") or ""
        source = s3.rsplit("/", 1)[-1] if s3 else "knowledge_base"
    score = raw.get("score")
    try:
        score_f = round(float(score), 4) if score is not None else None
    except (TypeError, ValueError):
        score_f = None
    return {
        "id": f"c{rank + 1}",
        "source": source or "unknown",
        "text": text[:600],
        "score": score_f,
        "rank": rank + 1,
    }


def retrieve_local(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """ローカル索引から BM25 + 埋め込みハイブリッドで top_k 件を検索する。"""
    records = list(_load_local_chunk_records(_INDEX_EPOCH))
    docs = [r["text"] for r in records]
    bm25 = _bm25_scores(query, docs)
    # ハイブリッド: BM25 で絞り込み → 埋め込みで再ランク
    pre_n = min(24, len(records))
    pre_idx = sorted(range(len(records)), key=lambda i: bm25[i], reverse=True)[:pre_n]
    if not pre_idx:
        return []

    cand_texts = [docs[i] for i in pre_idx]
    emb = embed_texts([query, *cand_texts])
    vectors = emb["embeddings"]
    q = vectors[0]
    scored: list[dict[str, Any]] = []
    max_bm = max((bm25[i] for i in pre_idx), default=1.0) or 1.0
    for j, i in enumerate(pre_idx):
        cos = _cosine(q, vectors[j + 1]) if len(vectors) > j + 1 else 0.0
        bm = bm25[i] / max_bm
        hybrid = 0.55 * cos + 0.45 * bm
        scored.append(
            {
                "text": records[i]["text"],
                "source": records[i]["source"],
                "score": round(hybrid, 4),
                "score_detail": {"cosine": round(cos, 4), "bm25": round(bm, 4)},
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return [_normalize_citation(c, rank=r) for r, c in enumerate(scored[:top_k])]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def retrieve_knowledge_base(query: str, top_k: int = 5) -> dict[str, Any]:
    """Bedrock KB またはローカル索引から引用を取得する。"""
    settings = get_settings()
    if settings.mock_mode or not settings.bedrock_knowledge_base_id:
        cites = retrieve_local(query, top_k=top_k)
        return {"citations": cites, "source": "local_index", "mock": True}

    from src.aws_clients import bedrock_agent_runtime

    resp = bedrock_agent_runtime().retrieve(
        knowledgeBaseId=settings.bedrock_knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": top_k}
        },
    )
    cites = []
    for i, r in enumerate(resp.get("retrievalResults", [])):
        cites.append(
            _normalize_citation(
                {
                    "text": (r.get("content") or {}).get("text", ""),
                    "score": r.get("score"),
                    "location": r.get("location"),
                },
                rank=i,
            )
        )
    return {"citations": cites, "source": "bedrock_kb", "mock": False}


def _system_for_use_case(use_case: str) -> str:
    base = USE_CASE_SYSTEM.get(use_case) or USE_CASE_SYSTEM["document_search"]
    # use_case に一致する管理プロンプトがあれば system は base のまま
    try:
        for p in list_prompts():
            if p.get("use_case") == use_case and "{{question}}" in (p.get("template") or ""):
                # template is user-facing; keep system separate
                return base
    except Exception:
        pass
    return base


def _synthesize_local_answer(query: str, cites: list[dict[str, Any]], use_case: str) -> str:
    if not cites:
        return (
            f"「{query}」に関連する文書が見つかりませんでした。"
            "samples/ への追加、または文書アップロード後に再検索してください。"
        )
    bullets = []
    for c in cites[:4]:
        snippet = re.sub(r"\s+", " ", c.get("text", ""))[:180]
        bullets.append(f"・[{c.get('source', 'doc')}] {snippet}")
    lead = {
        "faq": "手順の要点です。",
        "contract_review": "契約観点での確認ポイントです（一般情報）。",
        "callcenter": "お客様への案内案です。",
        "medical_search": "文書に基づく一般情報です（診断ではありません）。",
        "finance_advice": "文書に基づく一般情報です（投資助言ではありません）。",
    }.get(use_case, "根拠文書に基づく回答です。")
    return (
        f"{lead}\n\n質問: {query}\n\n"
        + "\n".join(bullets)
        + "\n\n上記出典を確認のうえ、詳細は原文をご参照ください。"
    )


def rag_answer(
    query: str,
    *,
    use_case: str = "document_search",
    top_k: int = 5,
    history: list[dict[str, str]] | None = None,
    apply_guardrail: bool = True,
) -> dict[str, Any]:
    """RAG パイプラインで回答・引用・ガードレール結果を返す。"""
    settings = get_settings()
    q = query.strip()
    if not q:
        return {"answer": "", "citations": [], "blocked": False, "use_case": use_case}

    if apply_guardrail and settings.enable_guardrails:
        g_in = apply_guardrails(q, source="INPUT")
        if g_in.get("action") == "GUARDRAIL_INTERVENED":
            return {
                "answer": (g_in.get("outputs") or [{"text": "[入力がブロックされました]"}])[0].get(
                    "text", "[入力がブロックされました]"
                ),
                "citations": [],
                "blocked": True,
                "guardrail": g_in,
                "use_case": use_case,
                "mock": g_in.get("mock", False),
            }

    # 本番 KB: RetrieveAndGenerate を1回だけ（二重 retrieve を避ける）
    if not settings.mock_mode and settings.bedrock_knowledge_base_id:
        from src.aws_clients import bedrock_agent_runtime

        hist_prefix = ""
        if history:
            turns = []
            for h in history[-6:]:
                role = "ユーザー" if h.get("role") == "user" else "アシスタント"
                turns.append(f"{role}: {h.get('content', '')[:400]}")
            hist_prefix = "会話履歴:\n" + "\n".join(turns) + "\n\n"

        resp = bedrock_agent_runtime().retrieve_and_generate(
            input={"text": hist_prefix + q},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": settings.bedrock_knowledge_base_id,
                    "modelArn": (
                        f"arn:aws:bedrock:{settings.aws_region}::foundation-model/"
                        f"{settings.bedrock_text_model_id}"
                    ),
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {"numberOfResults": top_k}
                    },
                },
            },
        )
        answer = (resp.get("output") or {}).get("text", "")
        raw_cites = resp.get("citations") or []
        cites: list[dict[str, Any]] = []
        for i, c in enumerate(raw_cites):
            refs = c.get("retrievedReferences") or []
            for ref in refs:
                cites.append(
                    _normalize_citation(
                        {
                            "text": (ref.get("content") or {}).get("text", ""),
                            "location": ref.get("location"),
                            "score": None,
                        },
                        rank=len(cites),
                    )
                )
            if not refs:
                cites.append(_normalize_citation({"text": str(c)[:400]}, rank=i))

        if apply_guardrail and settings.enable_guardrails:
            g_out = apply_guardrails(answer, source="OUTPUT")
            if g_out.get("action") == "GUARDRAIL_INTERVENED":
                answer = (g_out.get("outputs") or [{"text": answer}])[0].get("text", answer)
                return {
                    "answer": answer,
                    "citations": cites,
                    "blocked": True,
                    "guardrail": g_out,
                    "source": "bedrock_kb",
                    "mock": False,
                    "use_case": use_case,
                }

        return {
            "answer": answer,
            "citations": cites,
            "blocked": False,
            "source": "bedrock_kb",
            "mock": False,
            "use_case": use_case,
        }

    retrieved = retrieve_knowledge_base(q, top_k=top_k)
    cites = retrieved.get("citations") or []
    context = "\n\n".join(
        f"[{c.get('source')}] {c.get('text')}" for c in cites if c.get("text")
    )

    hist_block = ""
    if history:
        hist_block = "\n".join(
            f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')[:300]}"
            for h in history[-6:]
        )
        hist_block = f"会話履歴:\n{hist_block}\n\n"

    if settings.mock_mode:
        answer = _synthesize_local_answer(q, cites, use_case)
        return {
            "answer": answer,
            "citations": cites,
            "retrieval": {"source": retrieved.get("source"), "mock": True},
            "blocked": False,
            "mock": True,
            "use_case": use_case,
            "source": retrieved.get("source"),
        }

    system = _system_for_use_case(use_case)
    gen = generate_text(
        f"{hist_block}次の根拠のみで日本語回答してください。\n根拠:\n{context}\n\n質問: {q}",
        system=system,
        apply_guardrail=apply_guardrail,
    )
    return {
        "answer": gen["text"],
        "citations": cites,
        "retrieval": {"source": retrieved.get("source"), "mock": False},
        "blocked": False,
        "mock": gen.get("mock", False),
        "use_case": use_case,
        "source": retrieved.get("source"),
    }

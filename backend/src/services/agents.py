"""Bedrock Agents によるエージェント呼び出しサービス。"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.config import get_settings
from src.services.bedrock_text import generate_text
from src.services.rag import rag_answer


def invoke_agent(message: str, *, session_id: str | None = None) -> dict[str, Any]:
    """
    Bedrock Agents による業務自動化。
    資格情報/Agent ID が無い場合は RAG + ツール計画のモックにフォールバック。
    """
    settings = get_settings()
    sid = session_id or str(uuid4())

    if settings.mock_mode or not settings.bedrock_agent_id or not settings.enable_agents:
        rag = rag_answer(message, use_case="ai_agent")
        plan = generate_text(
            f"次の依頼を3ステップの業務自動化計画にしてください: {message}",
            system="あなたは企業向け AI エージェントです。",
            apply_guardrail=True,
        )
        return {
            "session_id": sid,
            "answer": rag["answer"],
            "plan": plan["text"],
            "citations": rag.get("citations", []),
            "mock": True,
            "agent": "mock-agent",
        }

    from src.aws_clients import bedrock_agent_runtime

    resp = bedrock_agent_runtime().invoke_agent(
        agentId=settings.bedrock_agent_id,
        agentAliasId=settings.bedrock_agent_alias_id or "TSTALIASID",
        sessionId=sid,
        inputText=message,
    )
    # ストリーミング応答の結合
    chunks = []
    for event in resp.get("completion", []):
        if "chunk" in event:
            part = event["chunk"].get("bytes")
            if part:
                chunks.append(part.decode("utf-8") if isinstance(part, (bytes, bytearray)) else str(part))
    return {
        "session_id": sid,
        "answer": "".join(chunks) or str(resp),
        "mock": False,
        "agent": settings.bedrock_agent_id,
    }

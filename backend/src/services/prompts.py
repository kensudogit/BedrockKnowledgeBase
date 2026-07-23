"""プロンプトテンプレートの CRUD（DynamoDB + メモリ fallback）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from boto3.dynamodb.conditions import Key

from src.aws_clients import dynamodb_resource
from src.config import get_settings

# DynamoDB Local 停止時のインメモリ fallback
_MEM: dict[str, dict[str, Any]] = {}


def _table():
    s = get_settings()
    return dynamodb_resource().Table(s.dynamodb_table_prompts)


def list_prompts() -> list[dict[str, Any]]:
    """登録済みプロンプトテンプレート一覧を返す。"""
    try:
        resp = _table().scan(Limit=100)
        return resp.get("Items", [])
    except Exception:
        return list(_MEM.values())


def get_prompt(prompt_id: str) -> dict[str, Any] | None:
    """prompt_id に一致するテンプレートを返す。"""
    try:
        resp = _table().get_item(Key={"prompt_id": prompt_id})
        return resp.get("Item")
    except Exception:
        return _MEM.get(prompt_id)


def upsert_prompt(
    *,
    name: str,
    template: str,
    use_case: str = "general",
    variables: list[str] | None = None,
    prompt_id: str | None = None,
) -> dict[str, Any]:
    """プロンプトテンプレートを新規作成または更新する。"""
    item = {
        "prompt_id": prompt_id or str(uuid4()),
        "name": name,
        "template": template,
        "use_case": use_case,
        "variables": variables or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }
    existing = get_prompt(item["prompt_id"]) if prompt_id else None
    if existing:
        item["version"] = int(existing.get("version", 1)) + 1
    try:
        _table().put_item(Item=item)
    except Exception:
        _MEM[item["prompt_id"]] = item
    return item


def render_prompt(prompt_id: str, values: dict[str, str]) -> dict[str, Any]:
    """{{変数}} を values で置換してレンダリングする。"""
    p = get_prompt(prompt_id)
    if not p:
        raise KeyError(prompt_id)
    text = p["template"]
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return {"prompt_id": prompt_id, "rendered": text, "name": p.get("name")}


def seed_default_prompts() -> list[dict[str, Any]]:
    """デモ用のデフォルトプロンプトセットを投入する。"""
    defaults = [
        {
            "name": "社内チャットボット",
            "use_case": "internal_chatbot",
            "template": "あなたは社内アシスタントです。丁寧に日本語で回答してください。\n質問: {{question}}",
            "variables": ["question"],
        },
        {
            "name": "契約書レビュー",
            "use_case": "contract_review",
            "template": "次の契約条項のリスクと改善点を箇条書きで指摘してください。\n---\n{{clause}}",
            "variables": ["clause"],
        },
        {
            "name": "FAQ回答",
            "use_case": "faq",
            "template": "FAQ根拠のみを使い、簡潔に回答してください。根拠が無ければ「不明」と答えてください。\nQ: {{question}}\n根拠:\n{{context}}",
            "variables": ["question", "context"],
        },
    ]
    out = []
    for d in defaults:
        out.append(upsert_prompt(**d))
    return out

"""Model registry + promotion for productionization (dev → staging → production)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.config import get_settings
from src.services import persist

STAGES = ("development", "staging", "production")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_models(stage: str | None = None) -> list[dict[str, Any]]:
    items = persist.load("model_registry")
    if stage:
        items = [m for m in items if m.get("stage") == stage]
    items.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
    return items


def get_model(model_id: str) -> dict[str, Any] | None:
    for m in persist.load("model_registry"):
        if m.get("model_id") == model_id:
            return m
    return None


def register_model(
    *,
    name: str,
    modality: str,
    version: str = "0.1.0",
    provider: str = "bedrock",
    model_uri: str = "",
    metrics: dict[str, Any] | None = None,
    experiment_id: str | None = None,
    project_id: str | None = None,
    stage: str = "development",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    settings = get_settings()
    if not model_uri:
        if modality == "text":
            model_uri = settings.bedrock_text_model_id
        elif modality == "image":
            model_uri = settings.bedrock_image_model_id
        elif modality == "embedding":
            model_uri = settings.bedrock_embed_model_id
        else:
            model_uri = f"local://{modality}"
    item = {
        "model_id": str(uuid4()),
        "name": name,
        "modality": modality,
        "version": version,
        "provider": provider,
        "model_uri": model_uri,
        "stage": stage,
        "metrics": metrics or {},
        "experiment_id": experiment_id,
        "project_id": project_id,
        "meta": meta or {},
        "created_at": _now(),
        "updated_at": _now(),
        "promoted_from": None,
    }
    persist.append("model_registry", item)
    return item


def promote_model(model_id: str, to_stage: str) -> dict[str, Any]:
    if to_stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    items = persist.load("model_registry")
    found = None
    for m in items:
        if m.get("model_id") == model_id:
            found = m
            break
    if not found:
        raise KeyError(model_id)
    order = {s: i for i, s in enumerate(STAGES)}
    if order[to_stage] < order.get(found.get("stage", "development"), 0):
        raise ValueError("cannot demote via promote; register a new version instead")
    # deactivate other production models of same modality when promoting to production
    if to_stage == "production":
        for m in items:
            if (
                m.get("modality") == found.get("modality")
                and m.get("stage") == "production"
                and m.get("model_id") != model_id
            ):
                m["stage"] = "staging"
                m["updated_at"] = _now()
                m["meta"] = {**(m.get("meta") or {}), "superseded_by": model_id}
    found["promoted_from"] = found.get("stage")
    found["stage"] = to_stage
    found["updated_at"] = _now()
    persist.rewrite("model_registry", items)
    return found


def active_models() -> dict[str, Any]:
    """Pinned production (else staging/dev) model per modality for runtime routing."""
    items = list_models()
    by_mod: dict[str, dict[str, Any]] = {}
    for stage in ("production", "staging", "development"):
        for m in items:
            mod = m.get("modality") or "unknown"
            if m.get("stage") == stage and mod not in by_mod:
                by_mod[mod] = m
    return {"active": by_mod, "count": len(by_mod)}

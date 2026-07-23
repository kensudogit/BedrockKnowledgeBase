"""API リクエストのテレメトリ記録と集計。"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services import persist


def record_event(
    *,
    path: str,
    method: str,
    status_code: int,
    latency_ms: int,
    project_id: str | None = None,
    use_case: str | None = None,
    model_id: str | None = None,
    mock: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """1 リクエスト分のテレメトリイベントを永続化する。"""
    event = {
        "event_id": str(uuid4()),
        "request_id": str(uuid4()),
        "project_id": project_id,
        "path": path,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "use_case": use_case,
        "model_id": model_id,
        "mock": mock,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    persist.append("telemetry", event)
    return event


def summarize(limit: int = 500) -> dict[str, Any]:
    """直近 limit 件のレイテンシ・エラー率・パス別集計を返す。"""
    events = persist.load("telemetry", limit=limit)
    if not events:
        return {
            "n_events": 0,
            "avg_latency_ms": 0,
            "by_path": {},
            "error_rate": 0.0,
            "mock_rate": 0.0,
        }
    lat = [e.get("latency_ms") or 0 for e in events]
    errors = sum(1 for e in events if int(e.get("status_code") or 200) >= 400)
    mocks = sum(1 for e in events if e.get("mock"))
    by_path: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "avg_latency_ms": 0, "_sum": 0})
    for e in events:
        p = e.get("path") or "?"
        by_path[p]["count"] += 1
        by_path[p]["_sum"] += e.get("latency_ms") or 0
    for p, v in by_path.items():
        v["avg_latency_ms"] = round(v["_sum"] / max(v["count"], 1), 1)
        del v["_sum"]
    return {
        "n_events": len(events),
        "avg_latency_ms": round(sum(lat) / len(lat), 1),
        "p95_latency_ms": sorted(lat)[max(0, int(len(lat) * 0.95) - 1)],
        "error_rate": round(errors / len(events), 3),
        "mock_rate": round(mocks / len(events), 3),
        "by_path": dict(by_path),
        "window": limit,
    }

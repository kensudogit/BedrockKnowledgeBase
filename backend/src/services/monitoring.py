"""本番 AI アプリ向けの継続的な精度・品質モニタリング。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.services import persist
from src.services.evaluation import list_evaluations
from src.services.feedback import feedback_summary, list_feedback
from src.services.telemetry import summarize as telemetry_summary


def record_monitor_snapshot(
    *,
    source: str = "manual",
    combined_score: float | None = None,
    approval_rate: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """評価・フィードバック・テレメトリから品質スナップショットを記録する。"""
    fb = feedback_summary()
    tele = telemetry_summary(200)
    evals = list_evaluations(1)
    latest_eval = (evals[0].get("metrics") or {}) if evals else {}
    snap = {
        "snapshot_id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "combined_score": combined_score
        if combined_score is not None
        else latest_eval.get("avg_combined_score"),
        "approval_rate": approval_rate if approval_rate is not None else fb.get("approval_rate"),
        "feedback_n": fb.get("n"),
        "avg_latency_ms": tele.get("avg_latency_ms"),
        "error_rate": tele.get("error_rate"),
        "mock_rate": tele.get("mock_rate"),
        "extra": extra or {},
    }
    persist.append("monitor_snapshots", snap)
    return snap


def monitor_series(limit: int = 48) -> list[dict[str, Any]]:
    """直近 limit 件のモニタリング時系列を返す。"""
    items = persist.load("monitor_snapshots")
    items.sort(key=lambda x: x.get("created_at", ""))
    return items[-limit:]


def quality_alerts(
    *,
    min_combined: float = 0.4,
    min_approval: float = 0.5,
    max_error_rate: float = 0.15,
) -> dict[str, Any]:
    """閾値とトレンドに基づく品質アラートを判定する。"""
    series = monitor_series(12)
    latest = series[-1] if series else record_monitor_snapshot(source="auto")
    alerts = []
    cs = latest.get("combined_score")
    if cs is not None and float(cs) < min_combined:
        alerts.append(
            {
                "severity": "high",
                "code": "accuracy_drop",
                "message": f"combined_score {cs} < {min_combined}",
            }
        )
    ar = latest.get("approval_rate")
    if ar is not None and float(ar) < min_approval and (latest.get("feedback_n") or 0) >= 5:
        alerts.append(
            {
                "severity": "medium",
                "code": "feedback_drop",
                "message": f"approval_rate {ar} < {min_approval}",
            }
        )
    er = latest.get("error_rate")
    if er is not None and float(er) > max_error_rate:
        alerts.append(
            {
                "severity": "high",
                "code": "error_rate",
                "message": f"error_rate {er} > {max_error_rate}",
            }
        )
    # トレンド: 直近3件 vs その前3件
    if len(series) >= 6:
        recent = [s.get("combined_score") for s in series[-3:] if s.get("combined_score") is not None]
        prev = [s.get("combined_score") for s in series[-6:-3] if s.get("combined_score") is not None]
        if recent and prev:
            if sum(recent) / len(recent) + 0.05 < sum(prev) / len(prev):
                alerts.append(
                    {
                        "severity": "medium",
                        "code": "accuracy_trend_down",
                        "message": "combined_score trending down vs prior window",
                    }
                )
    return {
        "latest": latest,
        "alerts": alerts,
        "healthy": len(alerts) == 0,
        "series_n": len(series),
    }


def delivery_status() -> dict[str, Any]:
    """CI/CD とランタイムの準備状況チェックリストを返す。"""
    from src.config import get_settings
    from src.services.model_registry import active_models, list_models

    s = get_settings()
    active = active_models()["active"]
    return {
        "app_env": s.app_env,
        "mock_mode": s.mock_mode,
        "require_api_key": s.require_api_key,
        "bedrock": {
            "knowledge_base": bool(s.bedrock_knowledge_base_id),
            "guardrail": bool(s.bedrock_guardrail_id),
            "agent": bool(s.bedrock_agent_id),
            "s3": bool(s.s3_documents_bucket),
        },
        "registry": {
            "n_models": len(list_models()),
            "production_modalities": [
                m for m, v in active.items() if v.get("stage") == "production"
            ],
            "active": {k: {"name": v.get("name"), "version": v.get("version"), "uri": v.get("model_uri")} for k, v in active.items()},
        },
        "monitoring": quality_alerts(),
        "feedback": feedback_summary(),
        "recent_feedback": list_feedback(5),
    }

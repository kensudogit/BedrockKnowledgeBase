"""
Lightweight DS notebook substitute (plain Python).
Usage (API running on :8180):
  py -3.12 notebooks/rag_eval_smoke.py
"""
from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8180"


def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    print("health:", get("/health").get("app_env"), "mock=", get("/health").get("mock_mode"))
    chat = post("/api/chat", {"message": "有給休暇の申請手順は？", "use_case": "faq", "mode": "rag"})
    print("chat citations:", len(chat.get("citations") or []))
    post(
        "/api/feedback",
        {
            "rating": 1,
            "session_id": chat.get("session_id"),
            "answer_preview": (chat.get("answer") or "")[:120],
            "use_case": "faq",
        },
    )
    ev = post("/api/evaluation/run", {"dataset_id": "golden_default", "name": "ds-smoke"})
    print("eval combined:", (ev.get("metrics") or {}).get("avg_combined_score"))
    print("ops:", json.dumps(get("/api/ops/summary")["feedback"], ensure_ascii=False))


if __name__ == "__main__":
    main()

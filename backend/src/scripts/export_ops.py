"""フィードバック・評価・テレメトリ等を JSONL でエクスポート（DS 分析用）。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.services import persist


def main() -> None:
    """永続化データを指定ディレクトリへ JSONL 形式で書き出す。"""
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="export_ops")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in ("feedback", "eval_runs", "telemetry", "ingest_jobs", "projects"):
        items = persist.load(name)
        path = out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"wrote {path} ({len(items)})")


if __name__ == "__main__":
    main()

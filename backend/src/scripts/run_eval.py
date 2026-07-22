"""CLI for DS/CI: python -m src.scripts.run_eval --dataset golden_default --fail-under 0.3"""
from __future__ import annotations

import argparse
import json
import sys

from src.services.evaluation import run_model_evaluation


def main() -> int:
    p = argparse.ArgumentParser(description="Run RAG evaluation dataset")
    p.add_argument("--dataset", default="golden_default")
    p.add_argument("--name", default=None)
    p.add_argument("--fail-under", type=float, default=0.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    run = run_model_evaluation(
        name=args.name,
        dataset_id=args.dataset,
        fail_under=args.fail_under if args.fail_under > 0 else None,
    )
    if args.json:
        print(json.dumps(run, ensure_ascii=False, indent=2))
    else:
        m = run["metrics"]
        print(
            f"dataset={m.get('dataset_id')} combined={m.get('avg_combined_score')} "
            f"keyword={m.get('avg_keyword_score')} retrieval={m.get('avg_retrieval_score')} "
            f"n={m.get('n_samples')}"
        )
        if m.get("fail_under") is not None:
            print("PASSED" if m.get("passed") else "FAILED")
    if run["metrics"].get("fail_under") is not None and not run["metrics"].get("passed"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

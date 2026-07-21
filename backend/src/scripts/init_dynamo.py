"""Create local DynamoDB tables for prompts / evals / sessions."""
from __future__ import annotations

import time

from src.aws_clients import dynamodb_resource
from src.config import get_settings
from src.services.prompts import seed_default_prompts


def ensure_table(name: str, key: str = "prompt_id") -> None:
    dyn = dynamodb_resource()
    try:
        existing = [t.name for t in dyn.tables.all()]
    except Exception as exc:  # noqa: BLE001
        print(f"list tables failed ({exc}); trying create {name}")
        existing = []
    if name in existing:
        print(f"exists: {name}")
        return
    params = {
        "TableName": name,
        "KeySchema": [{"AttributeName": key, "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": key, "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    }
    try:
        dyn.create_table(**params)
        print(f"created: {name}")
        time.sleep(0.5)
    except Exception as exc:  # noqa: BLE001
        print(f"skip {name}: {exc}")


def main() -> None:
    s = get_settings()
    ensure_table(s.dynamodb_table_prompts, "prompt_id")
    ensure_table(s.dynamodb_table_evals, "eval_id")
    ensure_table(s.dynamodb_table_sessions, "session_id")
    seeded = seed_default_prompts()
    print(f"seeded prompts: {len(seeded)}")


if __name__ == "__main__":
    main()

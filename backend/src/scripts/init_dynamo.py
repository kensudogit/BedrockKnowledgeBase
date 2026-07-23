"""ローカル DynamoDB テーブル（プロンプト/評価/セッション）の作成。"""
from __future__ import annotations

import time

from src.aws_clients import dynamodb_resource
from src.config import get_settings
from src.services.prompts import seed_default_prompts


def ensure_table(name: str, key: str = "prompt_id") -> None:
    """指定名の DynamoDB テーブルが無ければ PAY_PER_REQUEST で作成する。"""
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
    """環境に応じて DynamoDB テーブル作成またはメモリ上のプロンプトをシードする。"""
    s = get_settings()
    # Railway / モック: リモート DynamoDB をスキップ（AWS 接続タイムアウト回避）
    if not s.dynamodb_endpoint and s.mock_mode:
        seeded = seed_default_prompts()
        print(f"seeded prompts (memory): {len(seeded)}")
        return
    ensure_table(s.dynamodb_table_prompts, "prompt_id")
    ensure_table(s.dynamodb_table_evals, "eval_id")
    ensure_table(s.dynamodb_table_sessions, "session_id")
    seeded = seed_default_prompts()
    print(f"seeded prompts: {len(seeded)}")


if __name__ == "__main__":
    main()

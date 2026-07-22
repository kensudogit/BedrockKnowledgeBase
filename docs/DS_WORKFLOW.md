# データサイエンティスト / 受託・自社 運用ワークフロー

## 環境レイヤ

| 環境 | `APP_ENV` | `USE_BEDROCK_MOCK` | 用途 |
|---|---|---|---|
| development | development | true | ローカル試作・samples/Documents |
| staging | staging | false | 顧客 PoC・実 KB / Guardrails |
| production | production | false | 本番。`REQUIRE_API_KEY=true` |

## DS の典型フロー

1. **データセット作成** — `backend/datasets/*.json` を複製、または `POST /api/datasets`
2. **文書投入** — UI `/documents` または `POST /api/documents/kb-ingest`（S3+KB）
3. **評価実行** — `python -m src.scripts.run_eval --dataset golden_default --fail-under 0.4`
4. **比較** — `GET /api/evaluation/compare?a=<id>&b=<id>`
5. **フィードバック分析** — UI で 👍/👎 → `python -m src.scripts.export_ops`
6. **プロンプト改善** — `/prompts` で版管理 → `/chat` で再検証
7. **昇格** — staging で OK なら production の model/prompt/KB をピン留め

## プロジェクト分離（受託）

```bash
curl -X POST http://localhost:8180/api/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"client-a-poc","client_name":"A社","env":"staging"}'
```

以降リクエストに `X-API-Key` / `X-Project-Id` を付与。

## 観測

- `GET /api/ops/summary` — レイテンシ・エラー率・フィードバック・評価
- `GET /api/metrics/summary` — パス別レイテンシ

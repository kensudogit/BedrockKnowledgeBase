# BedrockKnowledgeBase — セキュリティレビュー（2026-10-25）

Skill: `aws-bedrock-production-security` に基づく実装レビューと残余リスク。

## 実装済み

| 領域 | 内容 |
|------|------|
| 認証 | Cognito **アクセストークン**（RS256/JWKS、`token_use=access`、`client_id` 検証）。開発用 HS256 JWT（`tenant_id` / `roles` クレーム）。API キー + プロジェクト（レガシー）。 |
| 認可 | `AuthPrincipal`（`sub`, `tenant_id`, `roles`）— **リクエスト body の tenant_id は信用しない**。 |
| RAG ACL | 取り込み時 `.acl.json` + メタ。検索前に `principal_can_read` でチャンク除外。Bedrock KB 検索時 `tenant_id` メタデータフィルタ（`shared` または自テナント）。 |
| 本番ゲート | `auth_enforce`: Cognito 設定時または `REQUIRE_API_KEY` / 本番環境で `/api/*` に Bearer または API キー必須。本番 Cognito 時は `POST /api/auth/token` 無効。 |
| 観測 | `/health` に `cognito_configured`, `auth_enforce`。`/api/auth/config` でフロント向け公開設定（秘密鍵なし）。 |
| IaC | `terraform/cognito.tf` — User Pool、PKCE SPA クライアント、groups、`custom:tenant_id` |
| ログイン UI | `/login`（Hosted UI + PKCE）、`/auth/callback`、Nav の AuthBar |

## リリース前チェック（verification.md より）

- [x] 無署名・改ざん JWT は middleware で 401（Cognito / dev JWT）
- [x] 別テナント文書はローカル RAG 索引から除外（`test_document_acl.py`）
- [ ] Cognito 実 Pool への結合テスト（JWKS 取得・groups / `custom:tenant_id`）
- [ ] Bedrock KB 側 S3 メタデータ `tenant_id` と DS 同期の E2E
- [ ] WAF / レート制限 / API Gateway 前段
- [ ] CloudTrail / 監査ログの PII マスキング
- [ ] CI: `pytest`, `pip-audit`, `bandit`

## 残余リスク

1. **Bedrock KB メタデータ**: 取り込みパイプラインで S3 オブジェクトに `tenant_id` メタを付与済みだが、KB インデックスへの反映は AWS 側設定に依存。未設定時は検索フィルタが空結果になる可能性あり。
2. **開発 JWT**: `JWT_SECRET` は本番 Cognito と併用しないこと。漏洩時は全テナントなりすまし可能。
3. **CORS**: `*` 許可時は `allow_credentials=False` だが、本番はオリジンを明示列挙すること。
4. **エージェント外部副作用**: `/api/agents/invoke` は別途 human-in-the-loop・冪等性の強化が必要（本 PR 範囲外）。
5. **ログ**: プロンプト全文のデフォルトログ出力は避ける（既存 telemetry の見直し推奨）。

## ロールバック

- Cognito 未設定 + `REQUIRE_API_KEY=false` + 非本番 → 従来の匿名 dev principal（ローカルのみ）。
- RAG ACL: `document_acl.principal_can_read` を常に True にしないこと。問題時は取り込み停止し `.acl.json` を監査。

## 未完了（運用で実施）

- IAM 実行ロールの Bedrock モデル ARN 最小化
- Secrets Manager / KMS
- 鍵ローテーション・インシデント手順

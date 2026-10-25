# Cognito（Terraform）

## 作成リソース

- User Pool（email サインイン、`custom:tenant_id`）
- グループ: `admin`, `editor`, `viewer`
- SPA App Client（**secret なし**、Authorization Code + PKCE）
- Hosted UI ドメイン: `{project}-{app_env}-auth` または `cognito_domain_prefix`

## 適用手順

```bash
cd terraform
terraform init
terraform plan    # terraform.tfvars を自動読込
terraform apply
```

本番 URL は `terraform.tfvars` の `cognito_callback_urls` / `cognito_logout_urls` に追加する。
ローカルだけ上書きする場合: `terraform plan -var-file=terraform.local.tfvars`

## 出力をアプリへ反映

| Terraform output | 環境変数 |
|------------------|----------|
| `cognito_user_pool_id` | `COGNITO_USER_POOL_ID` |
| `cognito_app_client_id` | `COGNITO_APP_CLIENT_ID` |
| `cognito_domain_prefix` | `COGNITO_DOMAIN_PREFIX` |
| `cognito_hosted_ui_base_url` | （API が region + prefix から組み立て） |

Lambda / Railway API に上記 3 変数を設定。フロントは `/api/auth/config` から Hosted UI URL を取得。

## ユーザー運用

1. Cognito コンソールまたは CLI でユーザーを作成
2. `custom:tenant_id` を設定（例: `acme-corp`）
3. グループ `viewer` / `editor` / `admin` に所属させる
4. フロント `/login` → **Cognito でログイン**

## 注意

- コールバック URL は App Client に **完全一致** 登録が必要
- 本番 `APP_ENV=production` では `POST /api/auth/token`（開発 JWT）は無効
- Bedrock KB の S3 メタデータ `tenant_id` と Cognito 属性を揃える

# Docker 開発環境

## 前提

- Docker Desktop（Compose V2）
- 初回: リポジトリルートで `.env` を用意

```powershell
copy .env.docker.example .env
```

## 標準スタック（ホットリロード）

Postgres · DynamoDB Local · FastAPI · Next.js

```powershell
docker compose up -d --build
```

| URL | 説明 |
|-----|------|
| http://localhost:3010 | Web UI（`/login` で開発 JWT または Cognito） |
| http://localhost:8180/docs | OpenAPI |
| http://localhost:8180/health | ヘルス |
| localhost:5435 | PostgreSQL |
| localhost:8001 | DynamoDB Local |

ログ:

```powershell
docker compose logs -f backend frontend
```

停止:

```powershell
docker compose down
```

## LocalStack（S3 等）— オプション

```powershell
docker compose --profile aws-local up -d --build
```

`AWS_ENDPOINT_URL=http://localstack:4566` を `.env` に追加し backend を再起動。

## Railway 同等の単一コンテナ

```powershell
docker compose -f docker-compose.prod-local.yml up -d --build
```

Next + API が 3010 で待受（`start.sh` 経由）。

## 認証（Docker）

- 既定: `JWT_SECRET`（`.env.docker.example`）→ `/login` → **開発トークン**
- Cognito: Terraform 出力を `.env` に設定。callback に `http://localhost:3010/auth/callback` を登録

## データ永続化

- Postgres: ボリューム `postgres_data`
- RAG アップロード: ホスト `./data/uploads` → コンテナ `/app/data/uploads`

## トラブルシュート

- **frontend が backend に繋がらない** — `INTERNAL_API_URL=http://backend:8180`（compose 既定）
- **401 on /api/** — `/login` でトークン取得、または `.env` の `JWT_SECRET` を確認
- **ポート競合** — `3010` / `8180` / `5435` を変更する場合は compose の ports も合わせる

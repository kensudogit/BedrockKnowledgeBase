# Bedrock Knowledge Base Platform

AWS 上のエンタープライズ向け生成 AI 基盤（ローカル開発 + Terraform IaC）。

## 主な機能

| # | 機能 | API |
|---|---|---|
| ① | Text Generation | `POST /api/text/generate` |
| ② | Image Generation | `POST /api/image/generate` |
| ③ | Embedding | `POST /api/embedding` |
| ④ | Guardrails | `POST /api/guardrails/apply` |
| ⑤ | Prompt Management | `GET/POST /api/prompts` |
| ⑥ | Model Evaluation | `POST /api/evaluation/run` |

追加: RAG `POST /api/rag/query` · Agents `POST /api/agents/invoke`

## 技術スタック

- **Backend**: Python 3.12 / FastAPI / boto3 / SQLAlchemy
- **Frontend**: Next.js 15 / React 19
- **DB**: PostgreSQL 16 + DynamoDB Local
- **AWS**: Bedrock, Knowledge Bases, Agents, S3, Lambda, API Gateway
- **IaC**: Terraform
- **Java**: Spring Boot 連携スタブ（`java-spring/`）

## 構成

```
S3
 ↓
Knowledge Base
 ↓
Bedrock
 ↓
Lambda
 ↓
API Gateway
 ↓
Web画面 (Next.js)
```

ローカルでは FastAPI が API Gateway + Lambda 相当を兼ね、`USE_BEDROCK_MOCK=true` で AWS 無し開発が可能です。

## 利用例

社内チャットボット / FAQ / 文書検索(RAG) / 契約書レビュー / コード生成 /
コールセンター支援 / 医療文書検索 / 金融アドバイス / OCR連携 / AIエージェント

## クイックスタート

前提: Docker Desktop, Python 3.12, Node.js 20+

```bat
setup.bat
```

```bat
cd backend
.venv\Scripts\activate
python run.py
```

```bat
cd frontend
npm run dev
```

- UI: http://localhost:3010
- API: http://localhost:8180/docs
- Postgres: `localhost:5435`
- DynamoDB Local: `localhost:8001`
- LocalStack S3: `localhost:4566`

## AWS 接続（本番モード）

`.env` を編集:

```env
USE_BEDROCK_MOCK=false
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-1
BEDROCK_KNOWLEDGE_BASE_ID=...
BEDROCK_GUARDRAIL_ID=...
BEDROCK_AGENT_ID=...
S3_DOCUMENTS_BUCKET=...
```

## Railway デプロイ

ルートの `Dockerfile` + `railway.toml` + `start.sh` で単一サービスとして公開します
（Next.js が `$PORT` で待受け、`/api/*`・`/health` を内部 uvicorn `:8180` へプロキシ）。

Railway ダッシュボードで Root Directory はリポジトリルートのままにし、必要なら変数を設定:

```env
USE_BEDROCK_MOCK=true
CORS_ORIGINS=*
DATABASE_URL=<Railway Postgres を Add した場合は自動>
DYNAMODB_ENDPOINT=
```

再デプロイ後、公開 URL の `/health` が `app: bedrock-knowledge-base` を返せば成功です。

## Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# values を編集
terraform init
terraform apply
```

S3 / DynamoDB / Lambda / API Gateway / IAM を作成し、Knowledge Base ID を環境変数へ注入します。

## ディレクトリ

```
BedrockKnowledgeBase/
├── backend/          # FastAPI（6機能 + RAG/Agents）
├── frontend/         # Next.js コンソール
├── lambda/           # API Gateway 用ハンドラ
├── terraform/        # IaC
├── samples/          # ローカル RAG デモ文書
├── java-spring/      # Bedrock Runtime 組込みスタブ
└── docker-compose.yml
```
"# BedrockKnowledgeBase" 

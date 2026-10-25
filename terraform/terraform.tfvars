# BedrockKnowledgeBase — 共有 Terraform 変数（秘密情報は含めない）
# バケット名は AWS アカウント内で一意にすること。衝突時は suffix を変更。

aws_region = "ap-northeast-1"
project    = "bkb"

documents_bucket_name = "bkb-kensudogit-documents-apne1"

app_env          = "staging"
use_bedrock_mock = "false"
require_api_key  = "false"

enable_cognito        = true
cognito_domain_prefix = ""

cognito_callback_urls = [
  "http://localhost:3010/auth/callback",
]

cognito_logout_urls = [
  "http://localhost:3010/login",
]

lambda_zip_path = "../lambda/dist/api.zip"

bedrock_text_model_id     = "anthropic.claude-3-5-sonnet-20240620-v1:0"
bedrock_embed_model_id    = "amazon.titan-embed-text-v2:0"
bedrock_knowledge_base_id = ""
bedrock_data_source_id    = ""
bedrock_guardrail_id      = ""
bedrock_guardrail_version = "DRAFT"

log_retention_days = 30

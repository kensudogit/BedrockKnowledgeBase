from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]
_ENV = _ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    aws_region: str = "ap-northeast-1"
    cors_origins: str = "http://localhost:3010"
    database_url: str = "postgresql://bkb_user:bkb_password@localhost:5435/bkb_db"
    dynamodb_endpoint: str = "http://localhost:8001"
    dynamodb_table_prompts: str = "bkb_prompts"
    dynamodb_table_evals: str = "bkb_evals"
    dynamodb_table_sessions: str = "bkb_sessions"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_endpoint_url: str = ""

    bedrock_text_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    bedrock_image_model_id: str = "amazon.titan-image-generator-v1"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_knowledge_base_id: str = ""
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = "DRAFT"
    bedrock_agent_id: str = ""
    bedrock_agent_alias_id: str = ""
    s3_documents_bucket: str = ""

    use_bedrock_mock: bool = True
    enable_guardrails: bool = True
    enable_agents: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def mock_mode(self) -> bool:
        return bool(self.use_bedrock_mock) or not (
            self.aws_access_key_id or self.bedrock_knowledge_base_id
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

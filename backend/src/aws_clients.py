"""AWS サービス（Bedrock / S3 / DynamoDB）の boto3 クライアントファクトリ。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3

from src.config import get_settings


def _base_kwargs() -> dict[str, Any]:
    """boto3 クライアント共通の接続パラメータを組み立てる。"""
    s = get_settings()
    kw: dict[str, Any] = {"region_name": s.aws_region}
    # DynamoDB Local / LocalStack は任意キー可。本番 AWS は実クレデンシャルが必要
    kw["aws_access_key_id"] = s.aws_access_key_id or "local"
    kw["aws_secret_access_key"] = s.aws_secret_access_key or "local"
    if s.aws_session_token:
        kw["aws_session_token"] = s.aws_session_token
    if s.aws_endpoint_url:
        kw["endpoint_url"] = s.aws_endpoint_url
    return kw


@lru_cache
def bedrock_runtime():
    """Bedrock Runtime クライアント（テキスト/画像/埋め込み生成）。"""
    return boto3.client("bedrock-runtime", **_base_kwargs())


@lru_cache
def bedrock_agent_runtime():
    """Bedrock Agent Runtime クライアント（エージェント呼び出し）。"""
    return boto3.client("bedrock-agent-runtime", **_base_kwargs())


@lru_cache
def bedrock_agent():
    """Bedrock Agent 管理 API クライアント。"""
    return boto3.client("bedrock-agent", **_base_kwargs())


@lru_cache
def s3_client():
    """S3 クライアント（ドキュメント保管）。"""
    return boto3.client("s3", **_base_kwargs())


@lru_cache
def dynamodb_resource():
    """DynamoDB リソース（プロンプト/評価/セッション永続化）。"""
    s = get_settings()
    kw = _base_kwargs()
    endpoint = s.effective_dynamodb_endpoint
    if endpoint:
        kw["endpoint_url"] = endpoint
    return boto3.resource("dynamodb", **kw)

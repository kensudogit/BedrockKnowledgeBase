from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3

from src.config import get_settings


def _base_kwargs() -> dict[str, Any]:
    s = get_settings()
    kw: dict[str, Any] = {"region_name": s.aws_region}
    # DynamoDB Local / LocalStack accept any keys; real AWS needs real creds.
    kw["aws_access_key_id"] = s.aws_access_key_id or "local"
    kw["aws_secret_access_key"] = s.aws_secret_access_key or "local"
    if s.aws_session_token:
        kw["aws_session_token"] = s.aws_session_token
    if s.aws_endpoint_url:
        kw["endpoint_url"] = s.aws_endpoint_url
    return kw


@lru_cache
def bedrock_runtime():
    return boto3.client("bedrock-runtime", **_base_kwargs())


@lru_cache
def bedrock_agent_runtime():
    return boto3.client("bedrock-agent-runtime", **_base_kwargs())


@lru_cache
def bedrock_agent():
    return boto3.client("bedrock-agent", **_base_kwargs())


@lru_cache
def s3_client():
    return boto3.client("s3", **_base_kwargs())


@lru_cache
def dynamodb_resource():
    s = get_settings()
    kw = _base_kwargs()
    if s.dynamodb_endpoint:
        kw["endpoint_url"] = s.dynamodb_endpoint
    return boto3.resource("dynamodb", **kw)

"""S3 ドキュメントアップロード + Bedrock Knowledge Base 取り込み（本番パス）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.config import get_settings
from src.services import persist
from src.services.documents import ingest_text
from src.services.rag import invalidate_local_index


def _record_job(job: dict[str, Any]) -> dict[str, Any]:
    persist.append("ingest_jobs", job)
    return job


def list_ingest_jobs(limit: int = 50) -> list[dict[str, Any]]:
    """取り込みジョブ履歴を新しい順に返す。"""
    items = persist.load("ingest_jobs")
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def ingest_to_knowledge_base(
    *,
    filename: str,
    content: str,
    content_type: str = "text/markdown",
    project_id: str | None = None,
) -> dict[str, Any]:
    """
    常にローカル索引を更新する。
    S3 + KB 設定済みかつ非モック時: S3 アップロード後 KB 取り込みを開始する。
    """
    settings = get_settings()
    job_id = str(uuid4())
    local = ingest_text(filename=filename, content=content, content_type=content_type)
    job: dict[str, Any] = {
        "job_id": job_id,
        "project_id": project_id,
        "filename": filename,
        "local_document_id": local.get("document_id"),
        "status": "local_indexed",
        "s3_key": None,
        "ingestion_job_id": None,
        "mock": settings.mock_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if settings.mock_mode or not settings.s3_documents_bucket:
        job["message"] = "ローカル索引のみ（S3_DOCUMENTS_BUCKET 未設定または mock）"
        return _record_job(job)

    try:
        from src.aws_clients import bedrock_agent, s3_client

        key = f"projects/{project_id or 'default'}/{job_id}_{filename}"
        s3_client().put_object(
            Bucket=settings.s3_documents_bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
        )
        job["s3_key"] = key
        job["status"] = "s3_uploaded"

        if settings.bedrock_knowledge_base_id:
            # データソース ID 設定時は StartIngestionJob を試行
            # コンソールからの同期も可能; DS ID 未設定時は手動同期
            ds_id = getattr(settings, "bedrock_data_source_id", "") or ""
            if ds_id:
                resp = bedrock_agent().start_ingestion_job(
                    knowledgeBaseId=settings.bedrock_knowledge_base_id,
                    dataSourceId=ds_id,
                    description=f"bkb ingest {filename}",
                    clientToken=job_id,
                )
                job["ingestion_job_id"] = (resp.get("ingestionJob") or {}).get("ingestionJobId")
                job["status"] = "kb_ingestion_started"
            else:
                job["message"] = "S3 アップロード済。BEDROCK_DATA_SOURCE_ID 未設定のため同期は手動/コンソール。"
                job["status"] = "s3_uploaded_pending_sync"
        invalidate_local_index()
    except Exception as exc:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(exc)
        job["message"] = "S3/KB 失敗。ローカル索引は維持。"

    return _record_job(job)


def get_ingestion_status(ingestion_job_id: str) -> dict[str, Any]:
    """Bedrock KB 取り込みジョブのステータスを取得する。"""
    settings = get_settings()
    if settings.mock_mode or not settings.bedrock_knowledge_base_id:
        return {"status": "MOCK", "ingestion_job_id": ingestion_job_id}
    ds_id = getattr(settings, "bedrock_data_source_id", "") or ""
    if not ds_id:
        return {"status": "UNKNOWN", "reason": "BEDROCK_DATA_SOURCE_ID not set"}
    from src.aws_clients import bedrock_agent

    resp = bedrock_agent().get_ingestion_job(
        knowledgeBaseId=settings.bedrock_knowledge_base_id,
        dataSourceId=ds_id,
        ingestionJobId=ingestion_job_id,
    )
    job = resp.get("ingestionJob") or {}
    return {
        "status": job.get("status"),
        "ingestion_job_id": ingestion_job_id,
        "statistics": job.get("statistics"),
        "raw": job,
    }

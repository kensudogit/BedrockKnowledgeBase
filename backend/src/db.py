"""PostgreSQL 接続・セッション管理と初期化。"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings, normalize_database_url

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """SQLAlchemy エンジンをシングルトン取得する。"""
    global _engine, SessionLocal
    if _engine is None:
        url = normalize_database_url(get_settings().database_url)
        _engine = create_engine(url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """トランザクション付き DB セッションをコンテキストマネージャで提供する。"""
    get_engine()
    assert SessionLocal is not None
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_database() -> None:
    """db/init.sql を読み込み、テーブルを初期化する（失敗時は無視）。"""
    sql = Path(__file__).resolve().parent.parent / "db" / "init.sql"
    if not sql.exists():
        return
    try:
        lines = [
            ln
            for ln in sql.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("--")
        ]
        statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
        with get_engine().begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception:
        pass


def database_ping() -> dict:
    """DB 接続可否を SELECT 1 で確認し、結果を辞書で返す。"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "configured": get_settings().database_configured}
    except Exception as exc:
        return {"ok": False, "configured": get_settings().database_configured, "error": str(exc)[:200]}

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, SessionLocal
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
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
    sql = Path(__file__).resolve().parent.parent / "db" / "init.sql"
    if not sql.exists():
        return
    try:
        with get_engine().begin() as conn:
            conn.execute(text(sql.read_text(encoding="utf-8")))
    except Exception:
        pass

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from .config import settings


engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False}, future=True)


def _table_exists(connection: Connection, name: str) -> bool:
    row = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": name},
    ).first()
    return row is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info('{table_name}')")).all()
    return {str(row[1]) for row in rows}


def _ensure_column(connection: Connection, table_name: str, column_name: str, sql_fragment: str) -> None:
    if column_name in _column_names(connection, table_name):
        return
    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_fragment}"))


def _run_sqlite_migrations() -> None:
    with engine.begin() as connection:
        if _table_exists(connection, "accounts"):
            _ensure_column(connection, "accounts", "gpmc_auth_data", "TEXT")
            _ensure_column(connection, "accounts", "gptk_cookie_jar", "JSON")
            _ensure_column(connection, "accounts", "gptk_session_state", "JSON")

        if _table_exists(connection, "jobs"):
            _ensure_column(connection, "jobs", "provider", "VARCHAR(32) NOT NULL DEFAULT 'gptk'")
            _ensure_column(connection, "jobs", "operation", "VARCHAR(120) NOT NULL DEFAULT 'unknown'")
            _ensure_column(connection, "jobs", "params", "JSON NOT NULL DEFAULT '{}'")
            _ensure_column(connection, "jobs", "dry_run", "BOOLEAN NOT NULL DEFAULT 1")
            _ensure_column(connection, "jobs", "cancel_requested", "BOOLEAN NOT NULL DEFAULT 0")
            _ensure_column(connection, "jobs", "progress", "FLOAT NOT NULL DEFAULT 0")
            _ensure_column(connection, "jobs", "status", "VARCHAR(40) NOT NULL DEFAULT 'queued'")


def initialize_database() -> None:
    from .models import Base

    Base.metadata.create_all(engine)
    _run_sqlite_migrations()


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

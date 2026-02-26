from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .config import settings


engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False}, future=True)


def initialize_database() -> None:
    from .models import Base

    Base.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

"""Database session helpers built on SQLModel."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from chatbot.core.config import AppSettings

EngineCacheKey = tuple[str, bool]
_ENGINE_CACHE: dict[EngineCacheKey, Engine] = {}


def create_engine_from_settings(settings: AppSettings, *, echo: bool = False) -> Engine:
    """Create (or reuse) a SQLModel engine based on ``AppSettings``."""

    dsn = settings.postgres.dsn
    cache_key: EngineCacheKey = (dsn, echo)
    if cache_key not in _ENGINE_CACHE:
        engine = create_engine(
            dsn,
            echo=echo,
            pool_pre_ping=True,
            future=True,
        )
        _ENGINE_CACHE[cache_key] = engine
    return _ENGINE_CACHE[cache_key]


def init_db(engine: Engine) -> None:
    """Create all tables for the metadata on the provided engine."""

    from . import models  # noqa: F401  Ensures models are imported before metadata usage.

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(settings: AppSettings, *, echo: bool = False) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    engine = create_engine_from_settings(settings, echo=echo)
    with Session(engine) as session:
        yield session

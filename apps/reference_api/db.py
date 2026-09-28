"""SQLAlchemy engine lifecycle for the reference-data API."""

from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from .config import Settings


@lru_cache(maxsize=4)
def _engine_for_url(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def get_engine(settings: Settings | None = None) -> Engine:
    resolved = settings or Settings.from_environment()
    return _engine_for_url(resolved.database_url)


def connection_for(settings: Settings | None = None):
    """Yield a transaction-scoped connection for one API request."""

    return get_engine(settings).begin()


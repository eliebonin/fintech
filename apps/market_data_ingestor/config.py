"""Minimal ingestor settings; no API version, tenant session or web dependencies."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class IngestorSettings:
    database_url: str
    environment: str

    @classmethod
    def from_environment(cls):
        return cls(database_url=os.environ.get('DATABASE_URL',
            'postgresql+psycopg://platform:platform_local_only@localhost:54329/platform_secm'),
            environment=os.environ.get('APP_ENV', 'local'))

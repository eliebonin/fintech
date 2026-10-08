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
            'postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'),
            environment=os.environ.get('APP_ENV', 'local'))

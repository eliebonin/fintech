"""Minimal ingestor settings; no API version, tenant session or web dependencies."""
from dataclasses import dataclass,field
import os


@dataclass(frozen=True)
class IngestorSettings:
    database_url: str = field(repr=False)
    environment: str

    @classmethod
    def from_environment(cls):
        return cls(database_url=os.environ.get('DATABASE_URL',''),
            environment=os.environ.get('APP_ENV', 'local'))

"""Environment-backed settings for the reference-data API."""

from dataclasses import dataclass
import os
from uuid import UUID


DEFAULT_DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"
DEFAULT_DEMO_TENANT_ID = UUID("00000000-0000-7000-8000-000000000011")


@dataclass(frozen=True)
class Settings:
    database_url: str
    environment: str
    api_version: str
    demo_tenant_id: UUID

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_tenant_id = os.environ.get("DEMO_TENANT_ID", str(DEFAULT_DEMO_TENANT_ID))
        return cls(
            database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
            environment=os.environ.get("APP_ENV", "local"),
            api_version=os.environ.get("REFERENCE_API_VERSION", "2026-09-01"),
            demo_tenant_id=UUID(raw_tenant_id),
        )


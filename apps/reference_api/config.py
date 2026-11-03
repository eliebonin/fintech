"""Environment-backed settings for the reference-data API."""

from dataclasses import dataclass, field
import os
from uuid import UUID


DEFAULT_DEMO_TENANT_ID = UUID("00000000-0000-7000-8000-000000000011")


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    environment: str
    api_version: str
    demo_tenant_id: UUID
    max_request_body_bytes: int = 1048576
    statement_timeout_ms: int = 30000
    lock_timeout_ms: int = 10000
    local_operator_key: str = field(default='', repr=False)
    local_operator_id: UUID = UUID('00000000-0000-7000-8000-000000000304')
    workload_process_limit: int = 2
    workload_global_limit: int = 2
    workload_tenant_limit: int = 1
    workload_retry_after: int = 5

    def __post_init__(self):
        if min(self.max_request_body_bytes,self.statement_timeout_ms,self.lock_timeout_ms)<=0:
            raise ValueError('API resource budgets must be positive')
        if min(self.workload_process_limit,self.workload_global_limit,self.workload_tenant_limit,self.workload_retry_after)<1:
            raise ValueError('Workload limits and retry interval must be positive')

    def validate_local_identity(self) -> None:
        """A local testing capability must never become deployment authentication."""
        if self.environment not in {'local','test','development'}:
            raise RuntimeError('Production authentication is not implemented; explicitly set APP_ENV=local for local testing only')
        if len(self.local_operator_key) < 32 or any(c.isspace() for c in self.local_operator_key):
            raise RuntimeError('LOCAL_ACCESS_OPERATOR_KEY must be a private random value of at least 32 characters; run scripts/configure_local_access.py')

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_tenant_id = os.environ.get("DEMO_TENANT_ID", str(DEFAULT_DEMO_TENANT_ID))
        return cls(
            database_url=os.environ.get("DATABASE_URL", ""),
            environment=os.environ.get("APP_ENV", ""),
            api_version=os.environ.get("REFERENCE_API_VERSION", "2026-09-01"),
            demo_tenant_id=UUID(raw_tenant_id),
            max_request_body_bytes=int(os.environ.get('REFERENCE_API_MAX_BODY_BYTES','1048576')),
            statement_timeout_ms=int(os.environ.get('REFERENCE_API_STATEMENT_TIMEOUT_MS','30000')),
            lock_timeout_ms=int(os.environ.get('REFERENCE_API_LOCK_TIMEOUT_MS','10000')),
            local_operator_key=os.environ.get('LOCAL_ACCESS_OPERATOR_KEY',''),
            local_operator_id=UUID(os.environ.get('LOCAL_PLATFORM_OPERATOR_ID','00000000-0000-7000-8000-000000000304')),
            workload_process_limit=int(os.environ.get('REFERENCE_API_WORKLOAD_PROCESS_LIMIT','2')),
            workload_global_limit=int(os.environ.get('REFERENCE_API_WORKLOAD_GLOBAL_LIMIT','2')),
            workload_tenant_limit=int(os.environ.get('REFERENCE_API_WORKLOAD_TENANT_LIMIT','1')),
            workload_retry_after=int(os.environ.get('REFERENCE_API_WORKLOAD_RETRY_AFTER','5')),
        )

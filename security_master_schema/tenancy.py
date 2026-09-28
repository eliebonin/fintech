"""Small tenant and effective-dated mapping guards for service boundaries."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Connection, select

from .models import strategy


class TenantScopeError(PermissionError):
    """Raised when a tenant-facing operation targets a strategy outside its scope."""


class AmbiguousMappingError(ValueError):
    """Raised when more than one verified mapping applies on the requested date."""


@dataclass(frozen=True)
class MappingRecord:
    """Minimal effective-dated mapping representation used before database lookup."""

    mapping_id: UUID
    valid_from: date
    valid_to: date | None
    status: str


@dataclass(frozen=True)
class OperationalMappingRecord:
    """Minimal approved tenant operational mapping used by the pure resolver."""

    mapping_id: UUID
    valid_from: date
    valid_to: date | None
    status: str


@dataclass(frozen=True)
class ModuleEntitlementRecord:
    """Minimal tenant-module entitlement used by the pure capability resolver."""

    entitlement_id: UUID
    module_code: str
    valid_from: date
    valid_to: date | None
    entitlement_state: str


def normalize_external_id(value: str, mode: str) -> str:
    """Return a conservative profile-directed identifier lookup value.

    Raw values remain immutable source evidence.  The normalised form is only
    for matching and therefore deliberately has no punctuation-removal or
    provider-specific rewriting in the initial implementation.
    """

    if mode == "EXACT":
        return value
    if mode == "TRIM_UPPER":
        return value.strip().upper()
    raise ValueError(f"Unsupported external identifier normalization mode: {mode}")


def assert_tenant_owns_strategy(connection: Connection, tenant_id: UUID, strategy_id: UUID) -> None:
    """Reject missing, legacy-unscoped, and cross-tenant strategy references."""

    owner_tenant_id = connection.scalar(
        select(strategy.c.tenant_id).where(strategy.c.strategy_id == strategy_id)
    )
    if owner_tenant_id != tenant_id:
        raise TenantScopeError("Strategy is outside the requesting tenant scope")


def select_effective_mapping(records: tuple[MappingRecord, ...], as_of_date: date) -> MappingRecord | None:
    """Return one verified mapping applicable on ``as_of_date`` or raise on ambiguity."""

    effective_records = tuple(
        record
        for record in records
        if record.status == "VERIFIED"
        and record.valid_from <= as_of_date
        and (record.valid_to is None or as_of_date <= record.valid_to)
    )
    if len(effective_records) > 1:
        raise AmbiguousMappingError("More than one verified mapping applies on the requested date")
    return effective_records[0] if effective_records else None


def select_effective_operational_mapping(
    records: tuple[OperationalMappingRecord, ...], as_of_date: date
) -> OperationalMappingRecord | None:
    """Return one approved mapping applicable to an inbound report business date."""

    effective_records = tuple(
        record
        for record in records
        if record.status == "APPROVED"
        and record.valid_from <= as_of_date
        and (record.valid_to is None or as_of_date <= record.valid_to)
    )
    if len(effective_records) > 1:
        raise AmbiguousMappingError("More than one approved operational mapping applies on the requested date")
    return effective_records[0] if effective_records else None


def resolve_effective_module_codes(
    records: tuple[ModuleEntitlementRecord, ...], as_of_date: date
) -> frozenset[str]:
    """Return capabilities granted to a tenant on an effective business date.

    User-level permissions and data entitlements are deliberately resolved by
    separate controls. This function only establishes the product modules a
    tenant is entitled to use.
    """

    granted_by_module: dict[str, list[ModuleEntitlementRecord]] = {}
    for record in records:
        if (
            record.entitlement_state == "GRANTED"
            and record.valid_from <= as_of_date
            and (record.valid_to is None or as_of_date <= record.valid_to)
        ):
            granted_by_module.setdefault(record.module_code, []).append(record)

    ambiguous_codes = tuple(code for code, matches in granted_by_module.items() if len(matches) > 1)
    if ambiguous_codes:
        raise AmbiguousMappingError(
            f"More than one granted tenant module entitlement applies on the requested date: {', '.join(sorted(ambiguous_codes))}"
        )
    return frozenset(granted_by_module)

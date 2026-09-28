"""Pure effective-dated tenant module-entitlement resolution rules."""

from datetime import date
from uuid import UUID

import pytest

from security_master_schema.tenancy import (
    AmbiguousMappingError,
    ModuleEntitlementRecord,
    resolve_effective_module_codes,
)


def test_resolver_returns_only_effective_granted_module_codes() -> None:
    records = (
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000901"), "TRADING", date(2026, 1, 1), None, "GRANTED"),
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000902"), "FUND_MANAGEMENT", date(2026, 1, 1), None, "SUSPENDED"),
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000903"), "UCITS_CONTROLS", date(2027, 1, 1), None, "GRANTED"),
    )

    assert resolve_effective_module_codes(records, date(2026, 8, 28)) == frozenset({"TRADING"})


def test_resolver_returns_no_code_for_revoked_module() -> None:
    records = (
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000904"), "VALUATION", date(2026, 1, 1), None, "REVOKED"),
    )

    assert resolve_effective_module_codes(records, date(2026, 8, 28)) == frozenset()


def test_resolver_rejects_ambiguous_effective_grants_for_one_module() -> None:
    records = (
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000905"), "TRADING", date(2026, 1, 1), None, "GRANTED"),
        ModuleEntitlementRecord(UUID("00000000-0000-7000-8000-000000000906"), "TRADING", date(2026, 6, 1), None, "GRANTED"),
    )

    with pytest.raises(AmbiguousMappingError):
        resolve_effective_module_codes(records, date(2026, 8, 28))

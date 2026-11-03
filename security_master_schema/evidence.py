"""Exact evidence encoding and bounded Decimal inputs shared across domains.

Keep canonical bytes stable: existing evidence hashes and retained identities
depend on these rules. This module owns no valuation formulas or HTTP concepts.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID


def finite_decimal(value: Decimal, name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f'{name} must be a finite Decimal')
    if len(value.as_tuple().digits) > 60 or abs(value.as_tuple().exponent) > 60 or abs(value.adjusted()) > 60:
        raise ValueError(f'{name} exceeds supported precision')
    if positive and value <= 0:
        raise ValueError(f'{name} must be positive')
    return value


def canonical_payload(value):
    """Canonical evidence uses exact decimal strings, never binary floats."""
    if isinstance(value, Decimal):
        finite_decimal(value, 'evidence')
        if value == 0:
            return '0'
        rendered = format(value, 'f')
        return rendered.rstrip('0').rstrip('.') if '.' in rendered else rendered
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Evidence timestamps must be timezone aware')
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError('Evidence mapping keys must be strings')
        return {key: canonical_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical_payload(item) for item in value]
    if isinstance(value, float):
        raise ValueError('Binary floats are not financial evidence')
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError('Unsupported financial evidence value')


def evidence_hash(payload: dict) -> str:
    encoded = json.dumps(canonical_payload(payload), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return sha256(encoded.encode('utf-8')).hexdigest()

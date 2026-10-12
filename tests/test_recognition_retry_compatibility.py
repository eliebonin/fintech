from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID
from dataclasses import asdict, replace
from apps.reference_api.repository import _trade_booking_fingerprint
from valuation.service import ValuationRequest


def test_omitted_recognition_fields_preserve_legacy_booking_identity():
    class Payload:
        properties = []
        def __init__(self, extra): self.extra = extra
        def model_dump(self, **kwargs):
            return dict(executingBrokerOrganisationId=None, traderPersonId=None,
                tradePurpose='INVESTMENT', marketActivity=None, tagIds=[], properties=[], externalReferences=[]) | self.extra
    old = _trade_booking_fingerprint(Payload({}), None, UUID(int=1))
    assert _trade_booking_fingerprint(Payload(dict(valuationEffectiveDate=None, valuationOverrideReason=None)), None, UUID(int=1)) == old
    assert _trade_booking_fingerprint(Payload(dict(valuationEffectiveDate='2026-10-08', valuationOverrideReason='Deferred')), None, UUID(int=1)) != old


def test_intraday_request_identity_preserves_existing_retry_keys():
    from valuation.storage import request_identity
    request = ValuationRequest(*[UUID(int=n) for n in range(1,6)],
        *[datetime(2026,10,n,tzinfo=timezone.utc) for n in (5,6,7)])
    old = asdict(request)
    # These keys did not exist in the historical request contract.
    for key in ('daily','predecessor_batch_id','recalculation_reason'): old.pop(key)
    assert request_identity(request) == old
    assert request_identity(replace(request, daily=True))['daily'] is True

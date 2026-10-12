from datetime import datetime,timezone
from uuid import UUID
import pytest
from pydantic import ValidationError
from apps.reference_api.valuation_contracts import ValuationCreate

def payload(**changes):
    return dict(strategyId=str(UUID(int=1)),policyId=str(UUID(int=2)),cutId=str(UUID(int=3)),
        reportingCurrencyId=str(UUID(int=4)),openingDate='2026-10-06',closingDate='2026-10-07',
        informationCutoff=datetime.now(timezone.utc).isoformat())|changes

def test_daily_dates_resolve_without_inventing_market_cutoff():
    value=ValuationCreate.model_validate(payload())
    assert value.resolved_cutoffs()==(datetime(2026,10,6,23,59,59,999999,tzinfo=timezone.utc),datetime(2026,10,7,23,59,59,999999,tzinfo=timezone.utc))
    assert value.daily is True

@pytest.mark.parametrize('changes',[dict(closingDate='2026-10-06'),dict(openingDate='2026-08-01'),
    dict(openingCutoff='2026-10-06T22:00:00Z'),dict(informationCutoff='2026-10-07T12:00:00Z')])
def test_ambiguous_or_incomplete_daily_requests_rejected(changes):
    with pytest.raises(ValidationError): ValuationCreate.model_validate(payload(**changes))

def test_source_correction_requires_explicit_predecessor_and_reason():
    with pytest.raises(ValidationError): ValuationCreate.model_validate(payload(predecessorBatchId=str(UUID(int=5))))
    value=ValuationCreate.model_validate(payload(predecessorBatchId=str(UUID(int=5)),recalculationReason='Corrected assessed source'))
    assert value.predecessor_batch_id==UUID(int=5)

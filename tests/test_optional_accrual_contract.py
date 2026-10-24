from dataclasses import asdict,replace
from datetime import datetime,timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from apps.reference_api.valuation_contracts import ValuationCreate
from valuation.service import ValuationRequest
from valuation.storage import request_identity


def payload():
    return dict(strategyId=uuid4(),policyId=uuid4(),cutId=uuid4(),reportingCurrencyId=uuid4(),
        openingDate='2026-09-29',closingDate='2026-10-01',informationCutoff=datetime.now(timezone.utc))


def test_accrual_mode_is_optional_by_default_and_strict_flag_is_a_boolean():
    assert ValuationCreate(**payload()).require_complete_accruals is False
    assert ValuationCreate(**(payload()|dict(requireCompleteAccruals=True))).require_complete_accruals is True
    for value in ('false','true',1,None):
        with pytest.raises(ValidationError): ValuationCreate(**(payload()|dict(requireCompleteAccruals=value)))


def test_old_default_request_retry_identity_is_preserved_but_strict_is_distinct():
    p=ValuationCreate(**payload());opening,closing=p.resolved_cutoffs()
    r=ValuationRequest(uuid4(),p.strategy_id,p.policy_id,p.cut_id,p.reporting_currency_id,opening,closing,p.information_cutoff)
    old=asdict(r);old.pop('require_complete_accruals');old.pop('daily');old.pop('predecessor_batch_id');old.pop('recalculation_reason')
    assert request_identity(r)==old
    assert request_identity(replace(r,require_complete_accruals=True))==old|dict(require_complete_accruals=True)

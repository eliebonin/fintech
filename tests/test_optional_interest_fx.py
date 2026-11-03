import pytest
from valuation.accrued_balance import optional_interest_fx


@pytest.mark.parametrize('message',['Missing or ambiguous governed FX currency pair',
    'FX input selection blocked: NO_ELIGIBLE_OBSERVATION','FX input selection blocked: NO_VALID_ENTITLEMENT'])
def test_optional_interest_omits_unavailable_fx_without_altering_shared_resolver(monkeypatch,message):
    def unavailable(*args):raise ValueError(message)
    monkeypatch.setattr('valuation.fx.resolve_fx',unavailable)
    result=optional_interest_fx(None,None,None,None,None)
    assert result==message


@pytest.mark.parametrize('message',['FX selection currency orientation or rate semantics mismatch',
    'FX requires explicit timing, bounded freshness and sealed governed calendar'])
def test_invalid_supplied_fx_is_not_reclassified_as_absence(monkeypatch,message):
    def invalid(*args):raise ValueError(message)
    monkeypatch.setattr('valuation.fx.resolve_fx',invalid)
    with pytest.raises(ValueError,match='FX'):
        optional_interest_fx(None,None,None,None,None)

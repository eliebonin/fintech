"""Availability explains missing/deferred inputs without changing financial amounts."""
import pytest
from valuation import measure_inputs


@pytest.mark.parametrize('product,name,status,invalid,expected',[
 ('EQUITY','marketValue','AVAILABLE',False,None),
 ('EQUITY','marketValue','LOCAL_ONLY',False,'FX_UNAVAILABLE'),
 ('EQUITY','marketValue','UNAVAILABLE',False,'MISSING_INPUT'),
 ('FX_FORWARD','economicExposure','MULTI_CURRENCY',False,None),
 ('FX_FORWARD','marketValue','UNAVAILABLE',False,'NOT_SUPPORTED_YET'),
 ('FUTURE','marketValue','UNAVAILABLE',False,'NOT_SUPPORTED_YET'),
 ('FUTURE','referenceNotional','UNAVAILABLE',False,'MISSING_INPUT'),
 ('FUTURE','marketValue','UNAVAILABLE',True,'INVALID_CONTRACT'),
 ('OPTION_BOOKING','marketValue','UNAVAILABLE',True,'NOT_SUPPORTED_YET'),
 ('SWAP','economicExposure','UNAVAILABLE',True,'INVALID_CONTRACT'),
])
def test_missing_inputs_and_deferred_support_are_distinct(product,name,status,invalid,expected):
    assert measure_inputs.measure_reason(product,name,status,contract_invalid=invalid)==expected

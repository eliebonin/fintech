"""Name/identifier selection is presentation, not pricing or instrument mutation."""
from copy import deepcopy
import pytest
from security_master_schema.instrument_display import make_instrument_display


@pytest.mark.parametrize('kind,symbol,tenant,expected',[
    ('EQUITY','AI',None,('TICKER','AI')),
    ('ETF','EQQQ',None,('TICKER','EQQQ')),
    ('BOND','BILL',None,('ISIN','GB00BSGRV302')),
    ('FUND_SHARE_CLASS',None,None,('ISIN','GB00BSGRV302')),
    ('ACTIVELY_MANAGED_CERTIFICATE',None,None,('ISIN','GB00BSGRV302')),
    ('STRUCTURED_PRODUCT','NOTE',None,('ISIN','GB00BSGRV302')),
    ('FUTURE','ESZ6',None,('CONTRACT_SYMBOL','ESZ6')),
    ('OPTION','SPX.202612.P.05800000',None,('CONTRACT_SYMBOL','SPX.202612.P.05800000')),
    ('FX_FORWARD',None,None,('ISIN','GB00BSGRV302')),
    ('SWAP',None,'CLIENT-SWAP-007',('TENANT_REFERENCE','CLIENT-SWAP-007')),
    ('DIGITAL_ASSET','BTC/USD',None,('TRADING_PAIR','BTC/USD')),
])
def test_product_aware_identity_uses_existing_business_identifiers(kind,symbol,tenant,expected):
    identifiers=[dict(scheme='FIGI',value='BBG000EXAMPLE'),dict(scheme='ISIN',value='GB00BSGRV302')]
    before=deepcopy(identifiers)
    result=make_instrument_display(name='Approved business name',kind=kind,identifiers=identifiers,
        symbol=symbol,venue='Example venue',currency='GBP',currency_role='quote',tenant_identifier=tenant)
    assert result['primaryName']=='Approved business name'
    assert result['identifier']==dict(scheme=expected[0],value=expected[1])
    assert result['context']==['Example venue','GBP quote']
    assert result['basis']=='CURRENT_ACCESSIBLE_METADATA'
    assert identifiers==before


def test_canonical_equity_does_not_choose_an_arbitrary_listing_ticker():
    result=make_instrument_display(name='Company',kind='EQUITY',identifiers=[dict(scheme='ISIN',value='GB00BSGRV302')])
    assert result['identifier']==dict(scheme='ISIN',value='GB00BSGRV302')


def test_missing_business_identifier_does_not_promote_a_generated_internal_code():
    result=make_instrument_display(name='Bespoke swap',kind='SWAP',search_aliases=['IMPORT_opaque_123'])
    assert result['identifier'] is None
    assert result['primaryName']=='Bespoke swap'
    assert result['context']==[]
    assert 'IMPORT_opaque_123' in result['searchText']


def test_name_and_identifier_fallbacks_are_explicit_and_never_generated():
    result=make_instrument_display(name=None,kind='FX_FORWARD',identifiers=[dict(scheme='FISN',value='Approved short description')])
    assert result['primaryName']=='Approved short description'
    assert result['identifier'] is None
    missing=make_instrument_display(name=None,kind='OPTION')
    assert missing['primaryName']=='Instrument name unavailable'
    assert missing['identifier'] is None


def test_registered_alternatives_are_used_without_guessing_names_from_symbols():
    result=make_instrument_display(name='Actual option name',kind='OPTION',identifiers=[dict(scheme='OCC_SYMBOL',value='REGISTERED_CONTRACT')])
    assert result['primaryName']=='Actual option name'
    assert result['identifier']==dict(scheme='OCC_SYMBOL',value='REGISTERED_CONTRACT')
    result=make_instrument_display(name='Debt instrument',kind='BOND',identifiers=[dict(scheme='CUSIP',value='123456789')])
    assert result['identifier']==dict(scheme='CUSIP',value='123456789')

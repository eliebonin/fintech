"""Preparation checks are deliberately separate from regulator acceptance."""
from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError


def facts(**changes):
    return dict(instrumentName='Example',instrumentType='EQUITY',tradeType='INVESTMENT',
        lifecycleStatus='BOOKED',quantity='100.123456789012',quantityUnit='SHARES',
        executionPrice='12.123456789012',priceBasis='UNIT_PRICE',priceCurrency='GBP',
        executionTime='2026-10-28T14:31:10.123456+00:00',bookingTerms={'quantityBasis':'UNITS'})|changes


def mapped():
    return dict(instrumentIsin='GB0002634946',buyerId='BUYER',sellerId='SELLER',
        capacity='AOTC',venueMic='XLON',investmentDecisionId='DECISION',executionDecisionId='EXECUTION')


def test_unknown_scope_never_becomes_nonreportable_for_missing_adapter():
    from regulatory_reporting.assessment import assess
    result=assess(facts(instrumentType='UNRECOGNISED'),firm_scope='UNASSESSED',mapping={})
    assert result['reportability']=='NEEDS_ASSESSMENT'
    assert result['included'] is False and result['readiness']=='INCOMPLETE'


@pytest.mark.parametrize('family',['EQUITY','ETP','FUND','ACTIVELY_MANAGED_CERTIFICATE','BOND',
    'STRUCTURED_PRODUCT','FUTURE','OPTION','SWAP','FX_FORWARD'])
def test_each_family_preserves_actual_execution_units_and_price(family):
    from regulatory_reporting.assessment import assess
    f=facts(instrumentType=family,quantityUnit='CONTRACTS')
    result=assess(f,firm_scope='IN_SCOPE',mapping=mapped(),decision='REPORTABLE')
    assert result['readiness']=='READY' and result['included']
    assert f['quantity']=='100.123456789012' and f['executionPrice']=='12.123456789012'
    assert result['validationLevel']=='PREPARATION_ONLY'


def test_hold_and_missing_mapping_are_distinct():
    from regulatory_reporting.assessment import assess
    ready=assess(facts(),firm_scope='IN_SCOPE',mapping=mapped(),decision='REPORTABLE',disposition='HOLD')
    assert ready['readiness']=='READY' and not ready['included']
    incomplete=assess(facts(),firm_scope='IN_SCOPE',mapping={},decision='REPORTABLE')
    assert incomplete['reportability']=='REPORTABLE' and incomplete['readiness']=='INCOMPLETE'
    assert 'buyerId' in incomplete['missingFields']


def test_cancelled_and_changed_source_cannot_be_new_ready_reports():
    from regulatory_reporting.assessment import assess
    for f,changed in [(facts(lifecycleStatus='CANCELLED'),False),(facts(),True)]:
        result=assess(f,firm_scope='IN_SCOPE',mapping=mapped(),decision='REPORTABLE',needs_reassessment=changed)
        assert not result['included'] and result['readiness']=='INCOMPLETE'


def test_zero_negative_prices_allowed_but_missing_execution_price_is_visible():
    from regulatory_reporting.assessment import assess
    for p in ['0','-1.001']:
        assert assess(facts(executionPrice=p),firm_scope='IN_SCOPE',mapping=mapped(),decision='REPORTABLE')['included']
    assert 'executionPrice' in assess(facts(executionPrice=None),firm_scope='IN_SCOPE',mapping=mapped(),decision='REPORTABLE')['missingFields']


def test_review_is_controlled_and_reasoned():
    from regulatory_reporting.contracts import Review
    for payload in [dict(expectedRevision=1,action='REPORTABLE',reason=''),
                    dict(expectedRevision=1,action='HOLD',reason=''),
                    dict(expectedRevision=1,action='REPORTABLE',reason='Checked',mapping={'quantity':'7'})]:
        with pytest.raises(ValidationError): Review.model_validate(payload)


def test_profile_lei_checksum_and_dates_are_validated():
    from regulatory_reporting.contracts import ProfileCreate,Prepare
    with pytest.raises(ValidationError):
        ProfileCreate(name='Entity',lei='A'*20,firmCategory='MIFID_FIRM',firmScope='IN_SCOPE',reason='Checked')
    with pytest.raises(ValidationError):
        Prepare(profileId=uuid4(),strategyId=uuid4(),fromDate='2026-10-29',toDate='2026-10-28')


def test_csv_does_not_lose_decimal_precision_or_execute_spreadsheet_labels():
    from regulatory_reporting.assessment import preparation_csv
    output=preparation_csv([dict(candidateId=str(uuid4()),revision=1,facts=facts(instrumentName='=HYPERLINK("x")'),mapping=mapped())])
    assert '100.123456789012' in output and '12.123456789012' in output
    assert "'=HYPERLINK" in output
    assert Decimal('100.123456789012')*Decimal('12.123456789012')>0

def test_new_reporting_schema_columns_are_documented():
    from security_master_schema.models import metadata
    tables=[t for t in metadata.tables.values() if t.schema=='reg']
    assert len(tables)==5
    assert all(column.comment for table in tables for column in table.c)

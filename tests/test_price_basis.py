"""Hand-derived conversion cases; absent evidence is never a factor of one."""
from datetime import date
from decimal import Decimal
import pytest


def normalize(*args, **kwargs):
    from market_data.price_basis import normalise_as_traded
    return normalise_as_traded(*args, **kwargs)


def proof(events=()):
    return dict(method='SPLIT_ONLY', anchorDate='2026-10-08', coverageStart='2020-01-01',
        coverageEnd='2026-10-08', complete=True, marketDate='2026-10-06',
        sourceReference='provider-vintage-1', splits=list(events))


def test_raw_is_not_changed():
    assert normalize(Decimal('80'), 'RAW', None, allow_split_conversion=False).valuation_value == Decimal('80')


@pytest.mark.parametrize('events, expected', [
    ([dict(date='2026-10-07', numerator='2', denominator='1')], '80'),
    ([dict(date='2026-10-07', numerator='1', denominator='2')], '20'),
    ([dict(date='2026-10-07', numerator='2', denominator='1'),
      dict(date='2026-10-08', numerator='4', denominator='1')], '320'),
    ([], '40')])
def test_split_conversion_uses_verified_complete_timeline(events, expected):
    value = normalize(Decimal('40'), 'SPLIT_ADJUSTED', proof(events), allow_split_conversion=True)
    assert value.valuation_value == Decimal(expected)
    assert value.source_value == Decimal('40')
    assert value.valuation_basis == 'AS_TRADED'


@pytest.mark.parametrize('changes', [dict(complete=False), dict(anchorDate=None),
    dict(method='DIVIDEND_AND_SPLIT'), dict(coverageEnd='2026-10-07'),
    dict(splits=[dict(date='2026-10-07', numerator='0', denominator='1')]),
    dict(splits=[dict(date='2026-10-07', numerator='2', denominator='-1')])])
def test_incomplete_or_invalid_proof_blocks(changes):
    with pytest.raises(ValueError):
        normalize(Decimal('40'), 'SPLIT_ADJUSTED', proof() | changes, allow_split_conversion=True)


@pytest.mark.parametrize('basis, evidence, allowed', [
    ('SPLIT_ADJUSTED', None, True), ('SPLIT_ADJUSTED', proof(), False),
    ('VENDOR_ADJUSTED', proof(), True), ('TOTAL_RETURN', proof(), True)])
def test_unproven_or_disallowed_sources_block(basis, evidence, allowed):
    with pytest.raises(ValueError):
        normalize(Decimal('40'), basis, evidence, allow_split_conversion=allowed)


def test_decimal_rounding_retains_unrounded_value_and_rejects_overflow():
    converted = normalize(Decimal('1'), 'SPLIT_ADJUSTED', proof([
        dict(date='2026-10-07', numerator='1', denominator='3')]), allow_split_conversion=True)
    assert converted.valuation_value == Decimal('0.333333333333')
    assert converted.evidence['rounding'] == 'ROUND_HALF_EVEN_12DP'
    assert converted.evidence['unroundedValue'].startswith('0.333333333333333')
    with pytest.raises(ValueError):
        normalize(Decimal('1e18'), 'RAW', None, allow_split_conversion=False)

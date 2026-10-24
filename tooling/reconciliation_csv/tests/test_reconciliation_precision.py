"""Owner-authorized truncation must not round away from zero or lose evidence."""
from decimal import Decimal
import pytest


@pytest.mark.parametrize('source,stored,delta',[
    ('21.7983761151268','21.798376115126','-0.0000000000008'),
    ('-16.8467618260486','-16.846761826048','0.0000000000006'),
    ('0.747406499446919','0.747406499446','-0.000000000000919'),
    ('1.0409059999999999','1.040905999999','-0.0000000000009999'),
    ('123456789012345678.123456789012','123456789012345678.123456789012','0'),
])
def test_native_decimal_keeps_maximum_precision_and_original(source,stored,delta):
    from tooling.reconciliation_csv.reconciliation_precision import native_decimal
    result=native_decimal(source)
    assert result['sourceValue']==source and result['value']==stored
    assert Decimal(result['delta'])==Decimal(delta)
    assert result['truncated']==(Decimal(delta)!=0)


def test_conversion_occurs_before_truncation_and_rejects_overflow():
    from tooling.reconciliation_csv.reconciliation_precision import native_decimal
    result=native_decimal('0.9967199999999999',scale='100')
    assert result['value']=='99.671999999999'
    assert Decimal(result['delta'])==Decimal('-0.0000000000009900')
    for value in ('NaN','Infinity','1000000000000000000','0.'+'1'*1000):
        with pytest.raises(ValueError):native_decimal(value)

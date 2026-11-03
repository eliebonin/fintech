"""Provider quote accrual is a per-100 price component, not position earnings."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal,localcontext,InvalidOperation


@dataclass(frozen=True)
class BondQuoteAccrual:
    accrued_per_100: Decimal
    quote_settlement_date: date
    source_reference: str


def exact_decimal(value,name):
    if not isinstance(value,Decimal) or not value.is_finite() or value.copy_abs()>=Decimal('1e18'):
        raise ValueError(f'{name} requires a finite exact decimal within supported precision')
    with localcontext() as ctx:
        ctx.prec=100
        if value!=value.quantize(Decimal('1e-12')):raise ValueError(f'{name} exceeds 12 decimal places; no silent rounding')
    return value


def decimal_text(value):
    if value==0:return '0'
    text=format(value,'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def validate_quote_accrual(component):
    if not isinstance(component,BondQuoteAccrual):raise ValueError('Typed quoted bond accrual required')
    exact_decimal(component.accrued_per_100,'Quoted accrued interest per 100')
    if type(component.quote_settlement_date) is not date:raise ValueError('Explicit quote settlement date required')
    if not isinstance(component.source_reference,str) or not component.source_reference.strip() or len(component.source_reference)>1000:
        raise ValueError('Explicit quote accrual source reference required')


def clean_quote(dirty_price,accrued_per_100):
    exact_decimal(dirty_price,'DIRTY price');exact_decimal(accrued_per_100,'Quoted accrued interest per 100')
    if dirty_price<=0:raise ValueError('Positive plain-bond DIRTY price required')
    with localcontext() as ctx:
        ctx.prec=100
        clean=dirty_price-accrued_per_100
    exact_decimal(clean,'Derived CLEAN price')
    if clean<=0:raise ValueError('Positive derived plain-bond CLEAN price required')
    return clean


def component_payload(component):
    validate_quote_accrual(component)
    return dict(accruedPer100=decimal_text(component.accrued_per_100),quoteSettlementDate=component.quote_settlement_date.isoformat(),
        sourceReference=component.source_reference.strip())


def per_100_quote(values):
    try:return len(values)==1 and Decimal(next(iter(values)))==100
    except (ValueError,InvalidOperation,TypeError):return False

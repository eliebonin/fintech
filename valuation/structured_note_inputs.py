"""Match supplied whole-note marks to immutable booked quotation economics."""
from datetime import date
from security_master_schema.structured_note_valuation import quotation_factors


def validate_note_divisor(values,expected):
    from decimal import Decimal,InvalidOperation
    try:
        if len(values)!=1:raise ValueError()
        factor=Decimal(values[0])
        if not factor.is_finite() or factor<=0 or factor!=expected:raise ValueError()
    except (InvalidOperation,TypeError,ValueError):
        raise ValueError('Selected whole-note quote divisor differs from booked quotation') from None


def note_mark_context(projection,subject,cutoff):
    conventions=set()
    trades={trade for bucket in projection.buckets if bucket.key.subject_id==subject for trade in bucket.trade_ids}
    for fact in projection.facts:
        b=fact.booking
        if (not b or fact.trade_id not in trades or b.subject_id!=subject
            or (b.valuation_effective_date or fact.effective_at.date())>cutoff.date()
            or not projection.request.daily and fact.effective_at>cutoff):continue
        proof=b.product_evidence or {};cv=proof.get('noteConvention') or {}
        if b.product_basis!='STRUCTURED_PRODUCT' or quotation_factors(cv,b.quantity_unit)!=(b.unit_multiplier,b.quote_factor):
            raise ValueError('Frozen compatible structured-note quotation required')
        maturity=proof.get('maturityDate')
        if maturity and cutoff.date()>date.fromisoformat(maturity):raise ValueError('Unclosed structured note after maturity requires Ops closure')
        factor=format(b.quote_factor,'f').rstrip('0').rstrip('.') if '.' in str(b.quote_factor) else str(b.quote_factor)
        conventions.add((cv['priceBasis'],cv['accrual'],factor))
    if len(conventions)!=1:raise ValueError('Unique compatible structured-note CLEAN/DIRTY quotation required; unlike bases need assessed conversion evidence')
    basis,accrual,factor=next(iter(conventions))
    from decimal import Decimal
    return (('STRUCTURED_PRICE_BASIS',basis),('STRUCTURED_ACCRUAL_BASIS',accrual)),Decimal(factor)

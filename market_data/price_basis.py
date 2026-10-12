"""Provider-neutral economic price normalization; never mutate source prices.

A split timeline requires assessed coverage and an explicit adjustment-reference
convention. An empty list on its own does not establish that coverage.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext


@dataclass(frozen=True)
class NormalisedPrice:
    source_value: Decimal
    valuation_value: Decimal
    valuation_basis: str
    evidence: dict


def effective_price_requirement(rule):
    return rule.get('price_requirement'), bool(rule.get('allow_split_conversion', False))


def _positive(value):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('INVALID_PRICE_BASIS_PROOF') from exc
    if not value.is_finite() or value <= 0:
        raise ValueError('INVALID_PRICE_BASIS_PROOF')
    return value


def normalise_as_traded(source_value, source_basis, proof, *, allow_split_conversion):
    source_value = _positive(source_value)
    factor = Decimal(1)
    frozen = dict(method='NATIVE_RAW')
    if source_basis=='RAW' and proof and proof.get('method')=='DERIVED_SPLIT_ONLY':
        if _positive(proof['valuationValue'])!=source_value:
            raise ValueError('INVALID_DERIVED_RAW_LINEAGE')
        frozen=dict(method='DERIVED_RAW',derivation=proof)
    with localcontext() as ctx:
        ctx.prec = 100
        if source_basis != 'RAW':
            if source_basis != 'SPLIT_ADJUSTED' or not allow_split_conversion:
                raise ValueError('INCOMPATIBLE_PRICE_BASIS')
            if not proof:
                raise ValueError('PRICE_BASIS_PROOF_MISSING')
            try:
                market = date.fromisoformat(proof['marketDate'])
                anchor = date.fromisoformat(proof['anchorDate'])
                start = date.fromisoformat(proof['coverageStart'])
                end = date.fromisoformat(proof['coverageEnd'])
                if (proof['method'] != 'SPLIT_ONLY' or proof['complete'] is not True
                        or not proof['sourceReference'] or not start <= market <= anchor <= end
                        or not isinstance(proof['splits'], list)):
                    raise ValueError('PRICE_BASIS_PROOF_INCOMPLETE')
                seen = set()
                for event in sorted(proof['splits'], key=lambda item: item['date']):
                    day = date.fromisoformat(event['date'])
                    if day in seen or not start <= day <= end:
                        raise ValueError('INVALID_PRICE_BASIS_PROOF')
                    seen.add(day)
                    numerator, denominator = _positive(event['numerator']), _positive(event['denominator'])
                    if market < day <= anchor:
                        factor *= denominator / numerator
                frozen = dict(proof)
            except (KeyError, TypeError, InvalidOperation) as exc:
                raise ValueError('INVALID_PRICE_BASIS_PROOF') from exc
        unrounded = source_value / factor
        rounded = unrounded.quantize(Decimal('0.000000000001'), rounding=ROUND_HALF_EVEN)
        if not Decimal(0) < rounded < Decimal('1e18'):
            raise ValueError('NORMALIZED_PRICE_OUT_OF_RANGE')
    evidence = frozen | dict(conversionVersion='as-traded-v1', sourceValue=str(source_value),
        sourceBasis=source_basis, valuationValue=str(rounded), valuationBasis='AS_TRADED',
        factor=str(factor), unroundedValue=str(unrounded), rounding='ROUND_HALF_EVEN_12DP')
    return NormalisedPrice(source_value, rounded, 'AS_TRADED', evidence)

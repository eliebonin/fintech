"""Normalize source DIRTY quotes, keeping strategy interest/stock inputs separate."""
from dataclasses import replace
from sqlalchemy import select
from security_master_schema import models as m
from market_data.bond_quotes import BondQuoteAccrual,clean_quote,component_payload,decimal_text,per_100_quote
from market_data.bond_quote_store import load_quote_accruals
from .economics import evidence_hash


def normalize_bond_selection(c,selected,information_cutoff):
    dimensions={}
    for code,value in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value)
        .where(m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id)):
        dimensions.setdefault(code,set()).add(value)
    quote=dimensions.get('BOND_PRICE_TYPE',set())
    if quote=={'CLEAN'}:return selected
    if quote!={'DIRTY'}:raise ValueError('Bond mark requires an explicit unique CLEAN or DIRTY quotation')
    if not per_100_quote(dimensions.get('QUOTE_FACTOR',set())):
        raise ValueError('DIRTY bond quotation requires an explicit per-100 nominal divisor')
    manual=(selected.pricing_evidence or {}).get('manualOverride')
    if manual:
        from datetime import date
        from decimal import Decimal
        if manual.get('quotedAccrualPer100') is None or not manual.get('quoteSettlementDate'):
            raise ValueError('DIRTY manual mark requires its reviewed paired quoted accrual')
        component=BondQuoteAccrual(Decimal(manual['quotedAccrualPer100']),date.fromisoformat(manual['quoteSettlementDate']),manual['sourceReference'])
        payload=component_payload(component);clean=clean_quote(selected.selected_value,component.accrued_per_100)
        proof=payload|dict(method='DIRTY_MINUS_REVIEWED_QUOTED_ACCRUAL_PER_100',version=1,manualOverrideId=manual['requestId'],
            observationId=None,dirtyPrice=decimal_text(selected.selected_value),cleanPrice=decimal_text(clean),quoteFactor='100',
            currencyId=str(selected.currency_id),marketDate=selected.pricing_date_used.isoformat(),componentHash=evidence_hash(payload),recordedAtUtc=manual['reviewedAt'])
        return replace(selected,valuation_value=clean,pricing_evidence=dict(selected.pricing_evidence or {},bondPriceNormalization=proof))
    row=load_quote_accruals(c,[selected.market_data_observation_id],information_cutoff).get(selected.market_data_observation_id)
    if row is None:
        raise ValueError('DIRTY bond price needs its matching quoted accrued interest per 100, known by the information cutoff. Supply a CLEAN price or the paired quote component; daily strategy interest cannot substitute.')
    component=BondQuoteAccrual(row['accrued_interest_per_100'],row['quote_settlement_date'],row['source_reference'])
    payload=component_payload(component)
    if (row['component_hash']!=evidence_hash(payload) or not selected.pricing_date_used
        or row['quote_settlement_date']<selected.pricing_date_used):
        raise ValueError('Quoted bond accrual evidence differs from its source price/date')
    observation=c.execute(select(m.market_data_observation.c.value_basis,m.market_data_observation.c.received_at_utc)
        .where(m.market_data_observation.c.market_data_observation_id==selected.market_data_observation_id)).mappings().one()
    if observation['value_basis']!='RAW' or row['recorded_at_utc']<observation['received_at_utc']:
        raise ValueError('DIRTY bond normalization requires native RAW quotation and consistent source receipt evidence')
    if selected.valuation_value is not None and selected.valuation_value!=selected.selected_value:
        raise ValueError('Share-price normalization cannot be applied to a DIRTY bond quotation')
    clean=clean_quote(selected.selected_value,component.accrued_per_100)
    proof=payload|dict(method='DIRTY_MINUS_QUOTED_ACCRUAL_PER_100',version=1,observationId=str(selected.market_data_observation_id),
        dirtyPrice=decimal_text(selected.selected_value),cleanPrice=decimal_text(clean),quoteFactor='100',
        currencyId=str(selected.currency_id),marketDate=selected.pricing_date_used.isoformat(),
        componentHash=row['component_hash'],recordedAtUtc=row['recorded_at_utc'].isoformat())
    # Share-adjustment basis (RAW/AS_TRADED) is independent of bond CLEAN/DIRTY.
    return replace(selected,valuation_value=clean,
        pricing_evidence=dict(selected.pricing_evidence or {},bondPriceNormalization=proof))

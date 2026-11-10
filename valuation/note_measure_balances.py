"""Exact assessed CLEAN-note stocks; no bond coupon-schedule reconstruction."""
from decimal import Decimal
from uuid import UUID
from .accruals import read_accruals,accrual_amounts
from security_master_schema.evidence import evidence_hash


def load_note_measure_stocks(c,request):
    day=request.closing_cutoff.date()
    return {row['instrument_id']:row for row in read_accruals(c,request.tenant_id,request.strategy_id,day,day,request.information_cutoff) if row['input_type']=='DAILY_INTEREST'}


def assessed_note_stock(rows,instrument,currency,nominal,*,compatible_positions):
    if compatible_positions!=1:raise ValueError('Assessed note stock cannot be duplicated across listing/currency positions')
    row=rows.get(UUID(str(instrument)))
    if row is None:raise ValueError('Exact-date assessed note closing balance is missing; daily earnings alone are not a stock')
    payload=row['payload'];values=payload.get('inputs')
    if evidence_hash(payload)!=row['input_hash']:raise ValueError('Assessed note closing-stock source hash differs')
    if row['currency_id']!=currency:raise ValueError('Assessed note stock currency differs from the quote currency')
    if not values or payload.get('eligibleNominal') is None:
        raise ValueError('Note market value needs a reconciled closing-stock bridge and assessed eligible nominal')
    if Decimal(str(payload['eligibleNominal']))!=nominal:raise ValueError('Assessed note stock nominal differs from the current position')
    values={key:Decimal(str(value)) for key,value in values.items()}
    amounts=accrual_amounts(values)
    if any(Decimal(str(payload.get('amounts',{}).get(key,'NaN')))!=value for key,value in amounts.items()):
        raise ValueError('Assessed note closing-stock evidence does not reconcile')
    closing=amounts['balanceLocal']
    if not nominal and closing:raise ValueError('Detached note receivable cannot be allocated to a flat note')
    return closing,dict(inputId=str(row['input_id']),revision=row['revision'],valueDate=row['value_date'].isoformat(),
        currencyId=str(currency),amount=str(closing),eligibleNominal=str(nominal),nominalBasis='CURRENT_SCOPED_NOTE_HOLDING',
        sourceStatus='ASSESSED_INPUT',basis='ASSESSED_NOTE_CLOSING_BRIDGE',sourceProofHash=evidence_hash(payload))

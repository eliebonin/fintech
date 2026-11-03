"""Retain exact derived stocks and explicitly identified orphan receivables."""
from dataclasses import asdict
from sqlalchemy import select
from . import tables as t
from .accrued_balance_tables import balance_snapshot
from .accrued_balance_inputs import balance_proof
from .economics import canonical_payload,evidence_hash

METHOD='accrued-interest-receivable-fx-v1'


def retain_balances(c,attempt_id,calculation):
    result=calculation.accrued_balance
    if result is None:return
    r=calculation.request;rows=[]
    for line in result.lines:
        for day in line.days:
            proof=canonical_payload(dict(day=asdict(day),sourceRefs=line.source_refs,convention='OPENING_STOCK_CLOSING_FX_MOVEMENTS'))
            b=day.balance
            rows.append(dict(attempt_id=attempt_id,tenant_id=r.tenant_id,strategy_id=r.strategy_id,
                instrument_id=line.instrument_id,currency_id=line.currency_id,reporting_currency_id=r.reporting_currency_id,
                value_date=b.value_date,opening_balance=b.opening,daily_earned=b.daily_earned,balance_movements=b.trade_movements,
                coupon_paid=b.coupon_paid,closing_balance=b.closing,opening_fx=day.opening_fx,closing_fx=day.closing_fx,
                fx_pnl=day.amount,basis=b.basis,fx_status='CALCULATED' if day.amount is not None else 'NOT_CALCULATED',
                input_hash=evidence_hash(proof),evidence=proof))
    if rows:c.execute(balance_snapshot.insert(),rows)


def stage_receivable(c,attempt_id,calculation,line,rounded):
    from .storage import selection_identity
    r=calculation.request
    owner=evidence_hash(dict(kind='ACCRUED_INTEREST_RECEIVABLE',tenant=r.tenant_id,strategy=r.strategy_id,instrument=line.instrument_id,currency=line.currency_id))
    proof=balance_proof(line)
    identity=canonical_payload(dict(method=METHOD,receivable=proof,components={'CARRY':line.amount},
        storageRounding=rounded['evidence'],openingCutoff=r.opening_cutoff,closingCutoff=r.closing_cutoff,
        policyId=r.policy_id,reportingCurrency=r.reporting_currency_id,selections=[selection_identity(s) for s in line.selections]))
    digest=evidence_hash(identity)
    prior=c.execute(select(t.attribution).where(t.attribution.c.tenant_id==r.tenant_id,t.attribution.c.strategy_id==r.strategy_id,
        t.attribution.c.value_date==r.closing_cutoff.date(),t.attribution.c.position_key==owner)
        .order_by(t.attribution.c.version.desc()).limit(1)).mappings().one_or_none()
    if prior and prior['input_hash']==digest:return owner,prior['attribution_id']
    evidence=canonical_payload(dict(identity=identity,resultFormat='ACCRUED_RECEIVABLE_V1',economicInputs=[proof],
        balanceSourceAttemptId=attempt_id,receivableScope=dict(tenantId=r.tenant_id,strategyId=r.strategy_id,
            instrumentId=line.instrument_id,currencyId=line.currency_id),
        informationCutoff=r.information_cutoff,scope='ACCRUED_INTEREST_RECEIVABLE',selections=line.selections,
        storageRounding=rounded['evidence'],resolutionSnapshotIds=calculation.accrued_balance.snapshot_ids,
        appliedRules=[dict(code='ACCRUED_INTEREST_OPENING_STOCK_FX',version=1,evidenceRefs=[],
            explanation='Outstanding interest remains separately FX-exposed after the security holding closes; opening local stock times daily reporting-per-local FX change. No cash, market mark or trade is invented.')]))
    identity=c.scalar(t.attribution.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,attempt_id=attempt_id,
        position_key=owner,subject_id=line.instrument_id,value_date=r.closing_cutoff.date(),method=METHOD,
        version=prior['version']+1 if prior else 1,supersedes_attribution_id=prior['attribution_id'] if prior else None,
        input_hash=digest,currency_id=r.reporting_currency_id,market_pnl=rounded['market'],gross_pnl=rounded['gross'],net_pnl=rounded['net'],
        components=canonical_payload(rounded['components']),evidence=evidence).returning(t.attribution.c.attribution_id))
    return owner,identity


def valid_receivable_without_market_data(item):
    """Only a proved identity/zero-exposure receivable can lack provider FX."""
    from decimal import Decimal
    try:
        evidence=item['evidence'];proof=evidence['identity']['receivable']
        if item['method']!=METHOD or evidence['resultFormat']!='ACCRUED_RECEIVABLE_V1' or str(item['subject_id'])!=proof['instrumentId']:return False
        if not proof['sourceRefs'] or not proof['days']:return False
        if not any(d['amount'] is not None for d in proof['days']):return False
        for day in proof['days']:
            if day['amount'] is None:continue
            if Decimal(day['amount'])!=0:return False
            if Decimal(day['balance']['opening'])==0:continue
            if proof['currencyId']!=str(item['currency_id']) or not Decimal(day['opening_fx'])==Decimal(day['closing_fx'])==1:return False
        return True
    except (KeyError,TypeError,ValueError,ArithmeticError):return False

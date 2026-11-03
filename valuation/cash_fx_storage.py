"""Immutable cash-owned result versions; never impersonate a traded security."""
from dataclasses import asdict
from sqlalchemy import select
from . import tables as t
from .cash_fx import METHOD
from .economics import canonical_payload,evidence_hash


def cash_owner(row):
    return f"cash:{row['cash_account_id']}:{row['cash_currency_id']}"


def stage_cash_line(c,attempt_id,calculation,line,rounded):
    from .storage import selection_identity
    r=calculation.request
    cash=canonical_payload(dict(version=1,convention='OPENING_BALANCE_EOD_MOVEMENTS',
        tenant_id=r.tenant_id,strategy_id=r.strategy_id,account_id=line.account_id,currency_id=line.currency_id,
        reporting_currency_id=r.reporting_currency_id,days=[asdict(day) for day in line.days],missing=line.missing))
    identity=dict(method=METHOD,cashFx=cash,components=line.components(),storageRounding=rounded['evidence'],
        openingCutoff=r.opening_cutoff,closingCutoff=r.closing_cutoff,policyId=r.policy_id,
        reportingCurrency=r.reporting_currency_id,selections=[selection_identity(s) for s in line.selections])
    digest=evidence_hash(identity)
    prior=c.execute(select(t.attribution).where(t.attribution.c.tenant_id==r.tenant_id,
        t.attribution.c.strategy_id==r.strategy_id,t.attribution.c.value_date==r.closing_cutoff.date(),
        t.attribution.c.cash_account_id==line.account_id,t.attribution.c.cash_currency_id==line.currency_id)
        .order_by(t.attribution.c.version.desc()).limit(1)).mappings().one_or_none()
    if prior and prior['input_hash']==digest:return prior['attribution_id']
    evidence=canonical_payload(dict(identity=identity,cashFx=cash,resultFormat='CASH_FX_V1',
        informationCutoff=r.information_cutoff,storageRounding=rounded['evidence'],selections=line.selections,
        resolutionSnapshotIds=calculation.cash.snapshot_ids,scope='CASH_FX_OPENING_BALANCE',
        appliedRules=[dict(code='CASH_FX_OPENING_BALANCE_EOD_MOVEMENTS',version=1,
            evidenceRefs=[],
            explanation='Opening signed native cash multiplied by the change in reporting-per-native FX; intraday movements are treated at closing FX. No new income is inferred from balance changes.')]))
    return c.scalar(t.attribution.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,attempt_id=attempt_id,
        cash_account_id=line.account_id,cash_currency_id=line.currency_id,value_date=r.closing_cutoff.date(),
        version=prior['version']+1 if prior else 1,supersedes_attribution_id=prior['attribution_id'] if prior else None,
        method=METHOD,input_hash=digest,currency_id=r.reporting_currency_id,market_pnl=rounded['market'],
        gross_pnl=rounded['gross'],net_pnl=rounded['net'],components=canonical_payload(rounded['components']),evidence=evidence)
        .returning(t.attribution.c.attribution_id))


def valid_cash_without_market_data(item):
    """Admit only evidenced native identity/zero-exposure cash, not missing FX."""
    from decimal import Decimal
    from uuid import UUID
    try:
        proof=item['evidence']['cashFx'];days=proof['days']
        if (item['method']!=METHOD or item['evidence']['resultFormat']!='CASH_FX_V1'
            or UUID(proof['account_id'])!=item['cash_account_id'] or UUID(proof['currency_id'])!=item['cash_currency_id']
            or UUID(proof['reporting_currency_id'])!=item['currency_id']
            or proof['convention']!='OPENING_BALANCE_EOD_MOVEMENTS' or not days):return False
        for day in days:
            if not day['opening']['cash_balance_id'] or not day['closing']['cash_balance_id'] or Decimal(day['amount'])!=0:return False
            if day['fx_mode']=='IDENTITY':
                if proof['currency_id']!=proof['reporting_currency_id'] or Decimal(day['opening_fx'])!=1 or Decimal(day['closing_fx'])!=1:return False
            elif day['fx_mode']=='ZERO_OPENING_EXPOSURE':
                if Decimal(day['opening']['amount'])!=0:return False
            else:return False
        return True
    except (KeyError,ValueError,TypeError,ArithmeticError):return False

"""Company/account cash snapshots. No trade creation and no implicit carry.

Only the TENANT_EOD convention is admitted here; legacy balance rows remain
untouched. Strategy locks serialize upload revisions and idempotent retries.
"""
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal,localcontext
from uuid import uuid4
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action
from .economics import canonical_payload,evidence_hash


class CashConflict(ValueError):
    pass


def latest_on_date(rows,day):
    latest={}
    for row in rows:
        if row['balance_as_of_date']!=day: continue
        key=(row['cash_account_id'],row['currency_id'])
        if key not in latest or row['revision']>latest[key]['revision']: latest[key]=row
    return list(latest.values())


def scoped_strategy(c,tenant,actor,strategy,write=False):
    require_strategy_action(c,tenant,actor,'VALUATION_RUN' if write else 'VALUATION_READ',strategy)
    query=select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_id==strategy,m.strategy.c.tenant_id==tenant)
    if write: query=query.with_for_update()
    if c.scalar(query) is None: raise LookupError('Strategy unavailable')


def accounts(c,tenant,actor,strategy):
    scoped_strategy(c,tenant,actor,strategy)
    return [dict(r) for r in c.execute(select(m.cash_account.c.cash_account_id,m.cash_account.c.display_label,
        m.cash_account.c.account_type,m.cash_account.c.custodian_organisation_id,m.organisation.c.display_name.label('company_name'))
        .join(m.organisation,m.organisation.c.organisation_id==m.cash_account.c.custodian_organisation_id)
        .where(m.cash_account.c.strategy_id==strategy,m.cash_account.c.status=='ACTIVE')
        .order_by(m.cash_account.c.display_label,m.cash_account.c.cash_account_id)).mappings()]


def create_account(c,tenant,actor,payload):
    scoped_strategy(c,tenant,actor,payload.strategy_id,True)
    if not c.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.organisation_id==payload.company_id,m.organisation.c.status=='ACTIVE')):
        raise LookupError('Active maintaining company required')
    old=c.execute(select(m.cash_account).where(m.cash_account.c.strategy_id==payload.strategy_id,
        m.cash_account.c.display_label==payload.label)).mappings().one_or_none()
    if old:
        if (old['custodian_organisation_id'],old['account_type'])!=(payload.company_id,payload.account_type):
            raise CashConflict('Account label already identifies a different company or account type')
        return old['cash_account_id']
    return c.scalar(m.cash_account.insert().values(strategy_id=payload.strategy_id,custodian_organisation_id=payload.company_id,
        display_label=payload.label,account_type=payload.account_type).returning(m.cash_account.c.cash_account_id))


def upload(c,tenant,actor,payload,key):
    scoped_strategy(c,tenant,actor,payload.strategy_id,True)
    if not key.strip() or len(key)>200: raise ValueError('Use a nonblank request key of at most 200 characters')
    fingerprint=evidence_hash(payload.model_dump(mode='json'))
    keys=[f'{key}:{i}' for i in range(len(payload.rows))]
    old=c.execute(select(m.cash_balance).where(m.cash_balance.c.strategy_id==payload.strategy_id,
        m.cash_balance.c.submission_key.in_(keys))).mappings().all()
    if old:
        if len(old)!=len(keys) or any(r['request_hash']!=fingerprint for r in old):
            raise CashConflict('Upload request key reused with different contents')
        return sorted([dict(r) for r in old],key=lambda r:keys.index(r['submission_key']))
    valid_accounts=set(c.scalars(select(m.cash_account.c.cash_account_id).where(
        m.cash_account.c.strategy_id==payload.strategy_id,m.cash_account.c.status=='ACTIVE',
        m.cash_account.c.custodian_organisation_id.is_not(None))))
    valid_currencies=set(c.scalars(select(m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')))
    prepared=[]
    for i,row in enumerate(payload.rows):
        if row.account_id not in valid_accounts: raise LookupError('Account unavailable in strategy')
        if row.currency_id not in valid_currencies: raise LookupError('Active currency required')
        prior=c.execute(select(m.cash_balance).where(m.cash_balance.c.strategy_id==payload.strategy_id,
            m.cash_balance.c.cash_account_id==row.account_id,m.cash_balance.c.currency_id==row.currency_id,
            m.cash_balance.c.balance_as_of_date==row.value_date,m.cash_balance.c.source_system_id=='TENANT_EOD')
            .order_by(m.cash_balance.c.revision.desc()).limit(1)).mappings().one_or_none()
        revision=prior['revision'] if prior else 0
        if revision!=row.expected_revision: raise CashConflict('Balance revision changed; reload and explicitly correct the current revision')
        prepared.append(dict(strategy_id=payload.strategy_id,cash_account_id=row.account_id,currency_id=row.currency_id,
            balance_as_of_date=row.value_date,balance_as_of_datetime_utc=datetime.combine(row.value_date,time.max,timezone.utc),
            balance_type='LEDGER',source_system_id='TENANT_EOD',amount=row.amount,source_reference=row.source_reference,
            note=row.note,revision=revision+1,supersedes_balance_id=prior['cash_balance_id'] if prior else None,
            correction_reason=row.correction_reason,submission_key=keys[i],request_hash=fingerprint,created_by_user_account_id=actor))
    # All ownership/revision checks precede writes; API transaction is atomic.
    return [dict(c.execute(m.cash_balance.insert().values(**item).returning(m.cash_balance)).mappings().one()) for item in prepared]


def read(c,tenant,actor,strategy,day,*,asof=None):
    scoped_strategy(c,tenant,actor,strategy)
    asof=asof or datetime.now(timezone.utc)
    rows=c.execute(select(m.cash_balance).where(m.cash_balance.c.strategy_id==strategy,
        m.cash_balance.c.balance_as_of_date==day,m.cash_balance.c.source_system_id=='TENANT_EOD',
        m.cash_balance.c.received_at_utc<=asof).order_by(m.cash_balance.c.cash_account_id,m.cash_balance.c.currency_id,
        m.cash_balance.c.revision)).mappings().all()
    return [dict(row) for row in rows]


def preview(c,tenant,actor,payload):
    """Exact-date translated balances; never represents movement P&L or fund NAV."""
    from .fx import resolve_fx
    from .service import ValuationRequest
    scoped_strategy(c,tenant,actor,payload.strategy_id)
    now=datetime.now(timezone.utc);day=payload.value_date
    if day>=now.date(): raise ValueError('EoD preview requires a completed past UTC date')
    policy=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==tenant,
        m.valuation_policy.c.valuation_policy_id==payload.policy_id,m.valuation_policy.c.status=='ACTIVE',
        m.valuation_policy.c.valid_from<=day)).mappings().one_or_none()
    if not policy or policy['strategy_id'] not in (None,payload.strategy_id) or (policy['valid_to'] and day>policy['valid_to']):
        raise ValueError('Active tenant pricing policy valid for strategy/date required')
    if not c.scalar(select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.valuation_cut_id==payload.cut_id)):
        raise ValueError('Known valuation cut required')
    if not c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_id==payload.reporting_currency_id,m.currency.c.status=='ACTIVE')):
        raise ValueError('Active reporting currency required')
    rows=latest_on_date(read(c,tenant,actor,payload.strategy_id,day,asof=now),day)
    expected=set(c.execute(select(m.cash_balance.c.cash_account_id,m.cash_balance.c.currency_id).where(
        m.cash_balance.c.strategy_id==payload.strategy_id,m.cash_balance.c.balance_as_of_date<=day,
        m.cash_balance.c.source_system_id=='TENANT_EOD',m.cash_balance.c.received_at_utc<=now).distinct()).all())
    actual={(row['cash_account_id'],row['currency_id']) for row in rows}
    if not expected or expected-actual: raise ValueError('Missing exact-date cash balances; upload each known account/currency, including explicit zero balances')
    request=ValuationRequest(tenant,payload.strategy_id,payload.policy_id,payload.cut_id,payload.reporting_currency_id,
        datetime.combine(day-timedelta(days=1),time.max,timezone.utc),datetime.combine(day,time.max,timezone.utc),now)
    currencies={r['currency_id'] for r in rows};rates={currency:resolve_fx(c,request,currency,payload.reporting_currency_id,day) for currency in currencies}
    from market_data.display_access import assert_dataset_display
    selections=[fx.selection for fx in rates.values() if fx.selection]
    assert_dataset_display(c,tenant,{s.dataset_id for s in selections},series_contexts=[(s.dataset_id,s.market_data_series_id) for s in selections])
    with localcontext() as ctx:
        ctx.prec=512
        items=[dict(snapshot=row,fx=rates[row['currency_id']].evidence,fxRate=rates[row['currency_id']].rate,
            reportingValue=row['amount']*rates[row['currency_id']].rate) for row in rows]
        total=sum((item['reportingValue'] for item in items),Decimal(0))
    proof=canonical_payload(dict(strategyId=payload.strategy_id,valueDate=day,reportingCurrencyId=payload.reporting_currency_id,
        policyId=payload.policy_id,cutId=payload.cut_id,informationCutoff=now,items=items,totalReportingValue=total,
        scope='DATED_CASH_VALUE_ONLY',status='PREVIEW_NOT_STAGED',limitations=['NOT_CASH_PNL','NOT_FULL_NAV','KNOWN_UPLOADED_SCOPES_ONLY']))
    return proof | {'inputHash':evidence_hash(proof)}

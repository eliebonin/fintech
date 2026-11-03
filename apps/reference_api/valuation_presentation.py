"""Current read-only labels and exact groupings of stored P&L components.

Never persist this metadata in a result or use current reference terms to explain
historical economics. Call batch decoration only after the existing DISPLAY gate.
"""
from decimal import Decimal, localcontext
from uuid import UUID
from sqlalchemy import select, or_, func
from security_master_schema import models as m
from security_master_schema.strategy_access import request_strategy_predicate
from valuation import tables as t
from valuation.economics import MARKET
from .valuation_source_coverage import source_coverage
from .instrument_display import load_instrument_displays
from valuation.review_coverage import position_attention
from valuation.accrued_balance_presentation import project_stocks


def component_display(item,reporting_currency_id=None,missing_by_instrument=None):
    components=item.get('components') or {}
    with localcontext() as ctx:
        ctx.prec=512
        others=[Decimal(str(v)) for k,v in components.items() if k not in MARKET and k!='ACCRUAL']
        other=format(sum(others,Decimal(0)),'f') if others else None
    evidence=item.get('evidence') or {}
    attention=position_attention(evidence,missing_by_instrument,item.get('subject_id'))
    return dict(interest=components.get('ACCRUAL'),other=other,attention=attention,
        accruedBalanceStocks=project_stocks(evidence,reporting_currency_id))


def _ids(values):
    result=set()
    for value in values:
        try: result.add(UUID(str(value)))
        except (ValueError,TypeError): pass
    return result


def _chunks(values):
    values=list(values)
    for index in range(0,len(values),500): yield values[index:index+500]


def _contexts(c,tenant,requests):
    strategies={}; policies={}; currencies={}
    for chunk in _chunks(_ids(r.get('strategy_id') for r in requests)):
        for row in c.execute(select(m.strategy).where(m.strategy.c.tenant_id==tenant,
                m.strategy.c.strategy_id.in_(chunk),request_strategy_predicate(c,tenant,'VALUATION_READ',m.strategy.c.strategy_id))).mappings():
            strategies[str(row['strategy_id'])]=f"{row['display_name']} · {row['strategy_code']}"
    for chunk in _chunks(_ids(r.get('policy_id') for r in requests)):
        for row in c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==tenant,
                m.valuation_policy.c.valuation_policy_id.in_(chunk),or_(m.valuation_policy.c.strategy_id.is_(None),
                request_strategy_predicate(c,tenant,'VALUATION_READ',m.valuation_policy.c.strategy_id)))).mappings():
            policies[str(row['valuation_policy_id'])]=f"{row['display_name']} · {row['policy_code']} · v{row['version_no']}"
    for chunk in _chunks(_ids(r.get('reporting_currency_id') for r in requests)):
        for row in c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(m.currency.c.currency_id.in_(chunk))):
            currencies[str(row.currency_id)]=row.currency_code
    return [dict(strategy=strategies.get(str(r.get('strategy_id'))),policy=policies.get(str(r.get('policy_id'))),
        currency=currencies.get(str(r.get('reporting_currency_id')))) for r in requests]


def decorate_runs(c,tenant,rows):
    requests=[(row.get('request_payload') or {})|{'strategy_id':row.get('strategy_id') or (row.get('request_payload') or {}).get('strategy_id')}
        for row in rows]
    for row,context in zip(rows,_contexts(c,tenant,requests)): row['display']=context
    return rows


def decorate_batch(c,tenant,batch):
    """Enrich one already-authorized batch; IDs only come from its retained facts."""
    if batch['summary'].get('evidenceAccess')=='DENIED': return batch
    items=batch.get('items',[])
    selections=[s for item in items for s in (item.get('evidence') or {}).get('selections',[])]
    unpriced=(batch['summary'].get('inputCoverage') or {}).get('unpricedPositions',[])
    selections.extend(s for row in unpriced for s in row.get('selections',[]))
    refs=_ids([item.get('subject_id') for item in items]+[
        r.get('instrumentId') for r in (batch['summary'].get('accrualCoverage') or {}).get('missing',[])])
    refs.update(_ids(row.get('subjectId') for row in unpriced))
    refs.update(_ids(gap.get('request',{}).get('subject_reference_node_id')
        for gap in (batch['summary'].get('inputCoverage') or {}).get('gaps',[])))
    currency_ids={batch['summary'].get('reportingCurrencyId')}
    currency_ids.update(row.get('currencyId') for row in unpriced)
    cash_coverage=batch['summary'].get('cashCoverage') or {}
    unpriced_cash=(batch['summary'].get('inputCoverage') or {}).get('unpricedCashAccounts',[])
    selections.extend(s for row in unpriced_cash for s in row.get('selections',[]))
    cash_ids=_ids([item.get('cash_account_id') for item in items]+[row.get('accountId') for row in cash_coverage.get('scopes',[])])
    cash_ids.update(_ids(row.get('accountId') for row in unpriced_cash))
    currency_ids.update(row.get('currencyId') for row in unpriced_cash)
    currency_ids.update(row.get('currencyId') for row in cash_coverage.get('scopes',[]))
    for item in items:
        evidence=item.get('evidence') or {}
        currency_ids.add(evidence.get('identity',{}).get('bucket',{}).get('key',{}).get('currency_id'))
        currency_ids.add(item.get('cash_currency_id'))
        for value in evidence.get('economicInputs',[]):
            payload=value.get('payload') or {}
            currency_ids.update([payload.get('currencyId'),payload.get('reportingCurrencyId')])
            if value.get('kind')=='ACCRUED_BALANCE_FX':currency_ids.add(value.get('currencyId'))
    currencies={}
    for chunk in _chunks(_ids(currency_ids)):
        for row in c.execute(select(m.currency).where(m.currency.c.currency_id.in_(chunk))).mappings():
            currencies[str(row['currency_id'])]=row['currency_code']
    displays=load_instrument_displays(c,tenant,refs)
    references={identity:' · '.join([display.primary_name,*([display.identifier.value] if display.identifier else []),*display.context])
        for identity,display in displays.items()}
    instrument_types={identity:dict(code=display.instrument_type,label=display.instrument_type_label)
        for identity,display in displays.items() if display.instrument_type}
    cash_accounts={}
    for chunk in _chunks(cash_ids):
        a=m.cash_account;s=m.strategy
        query=select(a.c.cash_account_id,a.c.display_label,m.organisation.c.display_name).select_from(
            a.join(s,a.c.strategy_id==s.c.strategy_id).outerjoin(m.organisation,m.organisation.c.organisation_id==a.c.custodian_organisation_id)).where(
            a.c.cash_account_id.in_(chunk),s.c.tenant_id==tenant,a.c.strategy_id==batch.get('strategy_id'),
            request_strategy_predicate(c,tenant,'VALUATION_READ',a.c.strategy_id))
        for row in c.execute(query):cash_accounts[str(row.cash_account_id)]=' · '.join(v for v in (row.display_name,row.display_label) if v) or 'Cash account name unavailable'
    datasets={}; rules={}; users={}
    for chunk in _chunks(_ids(s.get('dataset_id') for s in selections)):
        query=select(m.dataset.c.dataset_id,m.dataset.c.display_name,m.data_provider.c.display_name.label('provider')).select_from(
            m.dataset.join(m.provider_product).join(m.data_provider)).where(m.dataset.c.dataset_id.in_(chunk),
            or_(m.data_provider.c.owner_tenant_id.is_(None),m.data_provider.c.owner_tenant_id==tenant))
        for row in c.execute(query).mappings(): datasets[str(row['dataset_id'])]=f"{row['provider']} · {row['display_name']}"
    for chunk in _chunks(_ids(s.get('policy_rule_id') for s in selections)):
        query=select(m.valuation_policy_rule,m.valuation_policy.c.policy_code,m.valuation_policy.c.version_no).join(
            m.valuation_policy).where(m.valuation_policy_rule.c.valuation_policy_rule_id.in_(chunk),m.valuation_policy.c.tenant_id==tenant,
            or_(m.valuation_policy.c.strategy_id.is_(None),request_strategy_predicate(c,tenant,'VALUATION_READ',m.valuation_policy.c.strategy_id)))
        for row in c.execute(query).mappings():
            rules[str(row['valuation_policy_rule_id'])]=f"{row['policy_code']} v{row['version_no']} · rule {row['rule_sequence']} · {row['series_type']}"
    actor_ids=_ids([batch.get('staged_by')]+[r.get('actor_id') for r in batch.get('reviews',[])])
    for chunk in _chunks(actor_ids):
        query=select(m.user_account.c.user_account_id,m.person.c.display_name).join(m.person).where(
            m.user_account.c.user_account_id.in_(chunk),m.user_account.c.user_account_id.in_(select(
                m.tenant_user_account.c.user_account_id).where(m.tenant_user_account.c.tenant_id==tenant)))
        for row in c.execute(query): users[str(row.user_account_id)]=row.display_name
    request=batch['summary'].get('request') or {}
    context=_contexts(c,tenant,[request])[0]
    pending=c.scalar(select(func.count()).select_from(t.amendment).where(t.amendment.c.tenant_id==tenant,
        t.amendment.c.base_batch_id==batch['batch_id'],t.amendment.c.status=='PENDING'))
    missing_by_instrument={}
    for missing in (batch['summary'].get('accruedBalanceCoverage') or {}).get('missing',[]):
        missing_by_instrument.setdefault(str(missing.get('instrumentId')),[]).append(missing)
    result=dict(batch,items=[dict(item,display=component_display(item,batch['summary'].get('reportingCurrencyId'),
        missing_by_instrument)) for item in items])
    with localcontext() as ctx:
        ctx.prec=512
        totals={key:format(sum((Decimal(str(i['display'][key])) for i in result['items'] if i['display'][key] is not None),Decimal(0)),'f')
            if any(i['display'][key] is not None for i in result['items']) else None for key in ('interest','other')}
    result['presentation']=dict(references=references,instrumentTypes=instrument_types,
        instrumentDisplays={identity:display.model_dump(mode='json',by_alias=True) for identity,display in displays.items()},
        currencies=currencies,cashAccounts=cash_accounts,datasets=datasets,rules=rules,users=users,
        context=context,totals=totals,pendingAmendments=pending,labelBasis='CURRENT_ACCESSIBLE_METADATA',
        sourceCoverage=source_coverage(batch))
    return result

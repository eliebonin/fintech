"""Governed rate-exchange reference facts and canonical first-time materialization.

Caller owns authority, proposal review, transaction and audit. No HTTP imports,
engines, payments or curve valuation belong here.
"""
from datetime import datetime,timezone
from sqlalchemy import select,or_,exists
from security_master_schema import models as m
from security_master_schema.rate_swap_terms import RateSwapTerms
from security_master_schema.reference_visibility import require_visible


def _rows(c,table,predicate,lock=False):
    stmt=select(table).where(predicate).order_by(*table.primary_key.columns)
    return [dict(r) for r in c.execute(stmt.with_for_update() if lock else stmt).mappings()]


def _active(rows,label):
    if len(rows)!=1 or rows[0]['status']!='ACTIVE':raise ValueError('An active governed '+label+' is required')
    return rows[0]


def validate_references(c,tenant,terms:RateSwapTerms,*,lock=False):
    currency_ids={terms.notional_currency_id,terms.quote_currency_id}|{leg.currency_id for leg in terms.legs}
    currencies={r['currency_id']:r for r in _rows(c,m.currency,m.currency.c.currency_id.in_(currency_ids),lock)}
    if set(currencies)!=currency_ids or any(r['status']!='ACTIVE' for r in currencies.values()):raise ValueError('All rate-leg and quote currencies must be active')
    rate_ids={leg.rate_reference_id for leg in terms.legs}
    node_ids=rate_ids|{r['reference_node_id'] for r in currencies.values() if r['reference_node_id']}
    nodes={}
    for node in sorted(node_ids,key=str):
        _rows(c,m.financial_reference_node,m.financial_reference_node.c.reference_node_id==node,lock)
        _rows(c,m.reference_node_scope,m.reference_node_scope.c.reference_node_id==node,lock)
        nodes[node]=dict(require_visible(c,tenant,node))
    types=_rows(c,m.reference_node_type,or_(m.reference_node_type.c.reference_node_type_id.in_({r['reference_node_type_id'] for r in nodes.values()}),m.reference_node_type.c.type_code=='INSTRUMENT'),lock)
    for node in rate_ids:
        kind=_active([r for r in types if r['reference_node_type_id']==nodes[node]['reference_node_type_id']],'rate reference type')
        if kind['type_code']!='RATE_INDEX':raise ValueError('Both floating legs require governed RATE_INDEX references')
    day_ids={leg.day_count_convention_id for leg in terms.legs}
    days=_rows(c,m.day_count_convention,m.day_count_convention.c.day_count_convention_id.in_(day_ids),lock)
    if {r['day_count_convention_id'] for r in days}!=day_ids or any(r['status']!='ACTIVE' for r in days):raise ValueError('Both floating legs require active day-count conventions')
    instrument_types=_rows(c,m.instrument_type,m.instrument_type.c.type_code=='SWAP',lock)
    return dict(currency=currencies[terms.notional_currency_id],currencies=list(currencies.values()),
        rateReferences=[nodes[leg.rate_reference_id] for leg in terms.legs],dayCountConventions=days,
        referenceTypes=types,instrumentTypes=instrument_types,
        creationReferenceType=_active([r for r in types if r['type_code']=='INSTRUMENT'],'instrument reference type'),
        creationInstrumentType=_active(instrument_types,'swap instrument type'))


def validate_shell(c,tenant,node,expected_definition,terms,*,lock=False):
    """Complete only a private nonbookable identity; never amend a live contract."""
    _rows(c,m.financial_reference_node,m.financial_reference_node.c.reference_node_id==node,lock)
    scopes=_rows(c,m.reference_node_scope,m.reference_node_scope.c.reference_node_id==node,lock)
    ref=dict(require_visible(c,tenant,node))
    if ref['is_tradable'] or not any(s['scope_type']=='TENANT_PRIVATE' and s['owner_tenant_id']==tenant and s['status']=='ACTIVE' for s in scopes):
        raise ValueError('Only an owned non-tradable swap reference can be completed')
    instruments=_rows(c,m.instrument,m.instrument.c.instrument_node_id==node,lock)
    definitions=_rows(c,m.instrument_definition_version,m.instrument_definition_version.c.instrument_node_id==node,lock)
    current=[r for r in definitions if r['is_current']]
    if len(instruments)!=1 or len(current)!=1 or current[0]['instrument_definition_version_id']!=expected_definition or current[0]['status']!='APPROVED':
        raise ValueError('Reference definition changed; reload before completion')
    if current[0]['source_payload_id'] is None:raise ValueError('Reference completion requires its retained source receipt')
    source=_rows(c,m.source_payload,m.source_payload.c.source_payload_id==current[0]['source_payload_id'],lock)
    if len(source)!=1 or source[0]['tenant_id'] not in (None,tenant):raise ValueError('Reference source receipt is outside this tenant')
    instrument=instruments[0]
    type_code=c.scalar(select(m.instrument_type.c.type_code).where(m.instrument_type.c.instrument_type_id==instrument['instrument_type_id']))
    if type_code!='SWAP' or not instrument['is_current'] or instrument['base_currency_id']!=terms.notional_currency_id:
        raise ValueError('Reference completion must retain the swap identity and basis currency')
    for name in ('instrument_type_id','base_currency_id','effective_from','effective_to','sequence_no','asset_class','issuer_organisation_id'):
        if instrument[name]!=current[0][name]:raise ValueError('Reference header differs from its approved definition')
    for table,key in ((m.swap_definition_version,'instrument_definition_version_id'),(m.swap_terms,'instrument_node_id'),
                      (m.instrument_booking_convention,'instrument_node_id'),(m.instrument_dates,'instrument_node_id')):
        values=[r['instrument_definition_version_id'] for r in definitions] if table is m.swap_definition_version else [node]
        if _rows(c,table,table.c[key].in_(values),lock):raise ValueError('Reference already has contractual or booking terms')
    if c.scalar(select(exists().where(m.trade.c.trade_subject_reference_node_id==node,m.trade.c.trade_type!='RESET'))):
        raise ValueError('A reference with position executions cannot be completed through first-time creation')
    return instrument,current[0]


def materialize(c,tenant,actor,request,facts):
    terms=request.terms;target=request.existing_reference_id
    old=None
    if target:
        instrument,old=validate_shell(c,tenant,target,request.expected_reference_definition_id,terms,lock=True)
        node=target;sequence=instrument['sequence_no']+1
    else:
        node=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=facts['creationReferenceType']['reference_node_type_id'],
            canonical_name=request.canonical_name,is_tradable=True,status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
        sequence=1
    fields=dict(instrument_type_id=facts['creationInstrumentType']['instrument_type_id'],asset_class='DERIVATIVE',
        base_currency_id=terms.notional_currency_id,effective_from=terms.effective_date,effective_to=None,is_current=True,sequence_no=sequence)
    if old:fields['issuer_organisation_id']=instrument['issuer_organisation_id']
    if old:
        c.execute(m.instrument_definition_version.update().where(m.instrument_definition_version.c.instrument_definition_version_id==old['instrument_definition_version_id']).values(is_current=False,status='SUPERSEDED'))
        c.execute(m.instrument.update().where(m.instrument.c.instrument_node_id==node).values(**fields))
        c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==node).values(canonical_name=request.canonical_name,is_tradable=True))
    else:c.execute(m.instrument.insert().values(instrument_node_id=node,**fields))
    definition=c.scalar(m.instrument_definition_version.insert().values(instrument_node_id=node,**fields,status='APPROVED',
        source_payload_id=old['source_payload_id'] if old else None,approved_by_user_account_id=actor,approved_at_utc=datetime.now(timezone.utc)).returning(m.instrument_definition_version.c.instrument_definition_version_id))
    c.execute(m.swap_definition_version.insert().values(instrument_definition_version_id=definition,schema_version=terms.schema_version,economics_payload=terms.model_dump(mode='json',by_alias=True)))
    c.execute(m.instrument_dates.insert().values(instrument_node_id=node,effective_date=terms.effective_date,maturity_date=terms.maturity_date))
    c.execute(m.swap_terms.insert().values(instrument_node_id=node,swap_type=category(terms)))
    for number,leg in enumerate(terms.legs,1):
        c.execute(m.swap_leg.insert().values(swap_instrument_node_id=node,leg_number=number,leg_role='FUNDING',pay_receive=leg.direction,
            reference_node_id=leg.rate_reference_id,currency_id=leg.currency_id,spread=leg.spread))
    return node


def category(terms):return 'CROSS_CURRENCY' if len({leg.currency_id for leg in terms.legs})>1 else 'INTEREST_RATE'


from security_master_schema.rate_swap_terms import assert_materialized

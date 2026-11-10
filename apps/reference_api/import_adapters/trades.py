"""Tenant-aware NEW cash-trade templates and authoritative booking preparation."""
from decimal import Decimal,localcontext
from datetime import timezone
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking,validate_execution_date,lock_booking_strategy
from trading.booking_contracts import TradeBookingRequest
from ..trade_properties import get_trade_booking_context,list_trade_traders
from trading.annotations import validate_trade_annotations,normalize_property_value,TradeFieldError
from trading.annotations import restrict_selection
from trading.cash_reference import load_cash_booking_listing

SUPPORTED={'EQUITY','ETF','FUND','FUND_SHARE_CLASS'}


def column(key,label,required=False,choices=None,description=''):
    return dict(key=key,label=label,required=required,choices=choices or [],description=description)


def descriptor(c,tenant,actor,strategy):
    authorize_booking(c,tenant,actor,strategy_id=strategy)
    lock_booking_strategy(c,tenant,strategy)
    context=get_trade_booking_context(c,tenant,actor,strategy)
    currencies=list(c.scalars(select(m.currency.c.currency_code).where(m.currency.c.status=='ACTIVE').order_by(m.currency.c.currency_code)))
    cols=[column('sourceTradeId','Source trade ID',True,description='Permanent unique ID within this strategy and source namespace.'),
          column('listingId','Listing UUID',True,description='Copy the exact listing UUID from the catalogue. No ticker guessing.'),
          column('side','Side',True,['BUY','SELL']),column('quantity','Shares / fund units',True),
          column('executionPrice','Execution price',True),column('tradeDatetime','Execution timestamp',True,description='ISO text including offset, e.g. 2026-10-01T14:30:00Z'),
          column('settlementDate','Settlement date',True,description='YYYY-MM-DD text; no implicit settlement assumptions.'),
          column('tradeCurrency','Trade currency check',choices=currencies,description='Optional ISO code; must match the approved listing currency.'),
          column('tradePurpose','Purpose',choices=['INVESTMENT','REBALANCING','HEDGING','OTHER']),
          column('marketActivity','Market activity',choices=['PRIMARY','SECONDARY']),
          column('valuationEffectiveDate','Effective valuation date',description='Optional YYYY-MM-DD; override reason required when applicable.'),
          column('valuationOverrideReason','Valuation date override reason'),column('comment','Comment'),
          column('externalReference','External reference'),column('clientReference','Client reference'),column('brokerReference','Broker reference'),
          column('referenceSource','Reference namespace',description='Optional namespace for client/broker references; not the import source namespace.'),
          column('tagIds','Tags',description='Separate UUIDs or UUID — label values using |.')]
    for field,role,label in [('counterpartyOrganisationId','COUNTERPARTY','Counterparty'),('executingBrokerOrganisationId','EXECUTING_BROKER','Executing broker')]:
        query=select(m.organisation.c.organisation_id,m.organisation.c.display_name).where(m.organisation.c.status=='ACTIVE')
        query=restrict_selection(c,tenant,role,query,m.organisation.c.organisation_id)
        choices=[f'{r[0]} — {r[1]}' for r in c.execute(query.order_by(m.organisation.c.display_name,m.organisation.c.organisation_id))]
        cols.append(column(field,label,choices=choices))
    people=list_trade_traders(c,tenant,limit=100000)
    cols.append(column('traderPersonId','Trader',choices=[f"{p['personId']} — {p['displayName']}" for p in people]))
    tag_choices=[f"{t['tagId']} — {t['label']}" for t in context['tags']]
    cols.append(column('tagId','Single tag',choices=tag_choices,description='Use tagIds for multiple tags; do not repeat this selection there.'))
    for prop in context['properties']:
        choices=[]
        if prop['valueType']=='REFERENCE':
            r=m.reference_catalogue_record;catalogue=m.reference_catalogue
            query=select(r.c.record_version_id,r.c.code,r.c.label).join(catalogue,r.c.catalogue_id==catalogue.c.catalogue_id).where(
                catalogue.c.tenant_id==tenant,catalogue.c.status=='ACTIVE',r.c.catalogue_id==prop['catalogueId'],r.c.status=='ACTIVE')
            choices=[f'{v[0]} — {v[1]}: {v[2]}' for v in c.execute(query.order_by(r.c.code,r.c.record_version_id))]
        elif prop['valueType']=='BOOLEAN':choices=['TRUE','FALSE']
        cols.append(column('property:'+str(prop['definitionId']),prop['label'],prop['required'],choices,
            f"{prop['valueType']} · {prop.get('description') or prop['code']}"))
    profile=context['tradeProfile']
    standards={f['standardFieldKey']:f for f in profile['fields'] if f['standardFieldKey']}
    standard_columns={'counterpartyOrganisationId':'COUNTERPARTY','executingBrokerOrganisationId':'EXECUTING_BROKER','traderPersonId':'TRADER','comment':'COMMENT'}
    cols=[col for col in cols if col['key'] not in standard_columns or standards.get(standard_columns[col['key']],{}).get('requirement','NOT_USED')!='NOT_USED']
    for col in cols:
        if col['key'] in standard_columns:col['required']=standards[standard_columns[col['key']]]['requirement']=='REQUIRED'
    return dict(tenantId=str(tenant),strategyId=str(strategy),columns=cols,
        profileVersionId=str(profile['profileVersionId']),profileAssignmentRevision=profile['assignmentRevision'],configurationHash=profile['configurationHash'],
        tenantLabel=c.scalar(select(m.tenant.c.display_name).where(m.tenant.c.tenant_id==tenant)),
        strategyLabel=c.scalar(select(m.strategy.c.display_name).where(m.strategy.c.strategy_id==strategy)))


def identity(value):
    return str(UUID(value.split(' — ',1)[0].strip()))


def prepare(c,tenant,actor,strategy,values,*,validate=True):
    authorize_booking(c,tenant,actor,strategy_id=strategy)
    payload={key:value for key,value in values.items() if value and key in {
        'listingId','side','quantity','executionPrice','tradeDatetime','settlementDate','tradePurpose','marketActivity',
        'valuationEffectiveDate','valuationOverrideReason','comment','externalReference','counterpartyOrganisationId',
        'executingBrokerOrganisationId','traderPersonId'}}
    payload['strategyId']=str(strategy)
    for key in ('listingId','counterpartyOrganisationId','executingBrokerOrganisationId','traderPersonId'):
        if payload.get(key):payload[key]=identity(payload[key])
    for key in ('quantity','executionPrice'):
        try:value=Decimal(payload.get(key,''))
        except ArithmeticError as exc:raise TradeFieldError(key,'Enter a positive decimal as text, using a dot as the decimal separator.') from exc
        with localcontext() as ctx:
            ctx.prec=64
            if not value.is_finite() or value<=0 or value>=Decimal('1e18') or value!=value.quantize(Decimal('0.000000000001')):
                raise TradeFieldError(key,'Use a positive exact decimal within 18 integer and 12 fractional digits.')
        formatted=format(value,'f')
        payload[key]=formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
    properties=[]
    definitions={str(r.definition_id):r.value_type for r in c.execute(select(m.trade_property_definition).where(
        m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE')).mappings()}
    for key,value in values.items():
        if key.startswith('property:') and value:
            definition=key.removeprefix('property:');kind=definitions.get(definition)
            if kind=='BOOLEAN':
                if value not in ('TRUE','FALSE'):raise ValueError(f'{key}: choose TRUE or FALSE.')
                value=value=='TRUE'
            elif kind=='REFERENCE':value=identity(value)
            elif kind:value=normalize_property_value(value,kind,[])
            properties.append(dict(definitionId=definition,value=value))
    payload['properties']=sorted(properties,key=lambda p:p['definitionId'])
    payload['tagIds']=sorted(identity(v) for v in (values.get('tagIds','')+'|'+values.get('tagId','')).split('|') if v.strip())
    refs=[]
    for key,kind in [('clientReference','CLIENT_REFERENCE'),('brokerReference','BROKER_REFERENCE')]:
        if values.get(key):refs.append(dict(referenceType=kind,referenceValue=values[key],sourceSystemId=values.get('referenceSource') or None))
    if refs and payload.get('externalReference'):
        refs.append(dict(referenceType='SOURCE_TRADE_ID',referenceValue=payload.pop('externalReference')))
    payload['externalReferences']=sorted(refs,key=lambda r:(r['referenceType'],r.get('sourceSystemId') or '',r['referenceValue']))
    request=TradeBookingRequest.model_validate(payload)
    if not validate:return request,{}
    day=validate_execution_date(request.trade_datetime)
    listing=load_cash_booking_listing(c,tenant,request.listing_id,day)
    kind=c.scalar(select(m.instrument_type.c.type_code).join(m.instrument,m.instrument.c.instrument_type_id==m.instrument_type.c.instrument_type_id)
        .where(m.instrument.c.instrument_node_id==listing['instrument_node_id']))
    if kind not in SUPPORTED:raise ValueError('This release accepts equities, ETFs and funds only; use the product-specific booking page for other types.')
    if values.get('tradeCurrency') and values['tradeCurrency']!=listing['currency_code']:
        raise ValueError('tradeCurrency: must match the approved listing currency '+listing['currency_code'])
    lock_booking_strategy(c,tenant,strategy)
    annotations=validate_trade_annotations(c,tenant,request,actor_id=actor)
    from trading.profiles.resolution import frozen_configuration
    request=request.model_copy(update={'profile_assignment_revision':annotations.configuration['assignmentRevision']})
    return request,dict(tradeConfiguration=frozen_configuration(annotations.configuration),listingId=str(request.listing_id),instrumentId=str(listing['instrument_node_id']),
        currency=listing['currency_code'],instrumentType=kind,bookingSnapshot=listing['booking_snapshot'],
        annotations=[{k:str(v) if isinstance(v,UUID) else v for k,v in a.items()} for a in annotations])

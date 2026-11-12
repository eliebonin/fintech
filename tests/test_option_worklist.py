"""Real approved listed-option holdings; notification reads have no financial effects."""
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_option_booking_api import listing
from tests.test_valuation_service import valued
from tests.test_lifecycle_assistance import configure
from tests.test_lifecycle_entitlements import change
from tests.test_fx_forward_booking_api import request as api
from tests.test_product_booking_api import approve


@pytest.fixture(scope='module')
def cash_listing():
 node=approve(api('POST','/v1/option-proposals',dict(canonicalName='Synthetic European cash put '+uuid4().hex,effectiveFrom='2026-09-01',underlyingId=str(ids['mvp_sp500_price_index_node']),optionType='PUT',strike='5800',strikeCurrencyId=str(ids['usd_currency']),premiumCurrencyId=str(ids['usd_currency']),premiumMultiplier='100',deliverableUnits='100',expiryDate='2027-09-17',lastTradingAtUtc='2027-09-16T21:00:00Z',exerciseStyle='EUROPEAN',settlementMethod='CASH')))
 approve(api('POST','/v1/listing-proposals',dict(instrumentId=node,listing=dict(marketVenueId=str(ids['xlon_venue']),tradingSymbol='OPT_CASH_'+uuid4().hex[:8],tradingCurrencyId=str(ids['usd_currency']),quoteFactor='1',unitMultiplier='100',effectiveFrom='2026-09-01'))))
 from apps.reference_api.db import get_engine
 with get_engine().connect() as c:return str(c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==UUID(node))))


@pytest.fixture(params=['physical','cash'])
def option_context(request,listing,cash_listing,valued):
 from apps.reference_api.option_booking import book,load
 from apps.reference_api.contracts import OptionBookingRequest
 c,r,_=valued;selected=listing if request.param=='physical' else cash_listing
 _,terms=load(c,r.tenant_id,UUID(selected),as_of=date(2026,10,1))
 def execute(side='BUY',quantity='10',effect='OPEN',strategy=None):
  payload=OptionBookingRequest(listingId=selected,strategyId=strategy or r.strategy_id,side=side,quantity=quantity,executionPrice='2.5',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05',positionEffect=effect,counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint=terms.terms_fingerprint)
  return book(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()),'option-lifecycle-test').data.trade.trade_id
 trade=execute();change(c,3);configure(c,1,event='OPTION_EXPIRY',strategy=r.strategy_id)
 return c,r,terms.instrument_id,trade,execute,request.param


def read(c,r,**kwargs):
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 query=dict(fromDate=date(2026,1,1),toDate=date(2028,12,31),strategyId=r.strategy_id,eventType='OPTION_EXPIRY',includeEarlierOverdue=False)|kwargs
 return list_worklist(c,r.tenant_id,ids['demo_user_account'],WorklistQuery(**query))


def test_sourced_option_contracts_are_read_only_and_exact(option_context):
 from lifecycle.worklist_options import inspect_option
 from lifecycle.worklist_contracts import OptionInspection,WorklistResponse
 c,r,node,trade,execute,kind=option_context
 counts=lambda:tuple(c.scalar(select(func.count()).select_from(t)) for t in [m.trade,m.cash_balance,m.access_audit_event,m.bond_redemption_proposal,m.fx_maturity_posting])
 before=counts();result=WorklistResponse.model_validate(read(c,r))
 assert {x.milestoneKind for x in result.items}=={'LAST_TRADE','EXPIRY'}
 assert all(x.status!='BLOCKED' for x in result.items),[x.reasons for x in result.items]
 assert all(x.instrumentType=='OPTION' and Decimal(x.quantities[0].netQuantity)==10 for x in result.items)
 row=result.items[0];view=OptionInspection.model_validate(inspect_option(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row.milestoneKind))
 assert view.sourceFingerprint==row.sourceFingerprint and view.eventKey==row.eventKey
 assert view.premiumMultiplier=='100' and view.underlyingName and view.financialTreatment=='NOT_ASSESSED'
 assert (view.exerciseStyle,view.settlementMethod,view.optionType)==(('AMERICAN','PHYSICAL','CALL') if kind=='physical' else ('EUROPEAN','CASH','PUT'))
 assert view.deliverableUnits=='100' and view.optionTermsId
 assert counts()==before
 assert read(c,r,q=str(node).upper())['total']==result.total
 assert read(c,r,q='%')['total']==0
 assert read(c,r,offset=25)['items']==[] and read(c,r,offset=25)['total']==result.total


def test_closed_short_and_cancelled_contracts_use_ledger_state(option_context):
 c,r,node,trade,execute,kind=option_context
 execute('SELL','10','CLOSE');assert read(c,r)['total']==0
 short=execute('SELL','3')
 assert all(Decimal(row['quantities'][0]['netQuantity'])==-3 for row in read(c,r)['items'])
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==short)).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_lifecycle_event_id=uuid4(),sequence_no=2,event_type='CANCELLED',event_payload='{}'))))
 assert read(c,r)['total']==0


def test_option_selection_and_database_guard_reject_financial_tiers(option_context):
 from lifecycle.assistance import assistance_view,require_assistance,current_assistance_proof
 from sqlalchemy.exc import IntegrityError
 c,r,node,trade,execute,kind=option_context
 view=assistance_view(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'OPTION_EXPIRY')
 assert view['availableTiers']==[0,1] and not view['handlerSupported'] and all(not x['allowed'] for x in view['operations'].values())
 with pytest.raises(ValueError,match='notifications-only'):configure(c,2,event='OPTION_EXPIRY',strategy=r.strategy_id)
 with pytest.raises(PermissionError):require_assistance(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'OPTION_EXPIRY','DIRECT')
 with pytest.raises(PermissionError):current_assistance_proof(c,r.tenant_id,r.strategy_id,'OPTION_EXPIRY')
 source=dict(c.execute(select(m.strategy_lifecycle_assistance).where(m.strategy_lifecycle_assistance.c.strategy_id==r.strategy_id,m.strategy_lifecycle_assistance.c.event_type=='OPTION_EXPIRY')).mappings().one())
 with pytest.raises(IntegrityError),c.begin_nested():c.execute(m.strategy_lifecycle_assistance.insert().values(**(source|dict(selected_tier=3,revision=2,previous_revision=1))))
 configure(c,0,event='OPTION_EXPIRY',strategy=r.strategy_id);assert read(c,r)['total']==0


def test_revised_terms_and_missing_dates_never_assume_exercise_or_zero(option_context):
 from lifecycle.worklist_options import inspect_option
 c,r,node,trade,execute,kind=option_context
 row=read(c,r)['items'][0]
 c.execute(m.option_terms.update().where(m.option_terms.c.instrument_node_id==node,m.option_terms.c.is_current).values(strike_value=123))
 changed=read(c,r)['items'];assert changed and all(x['status']=='BLOCKED' and x['positionAssessed'] for x in changed)
 view=inspect_option(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row['milestoneKind'])
 assert view['sourceFingerprint']!=row['sourceFingerprint']
 c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==node).values(expiry_date=None))
 assert any(x['milestoneKind']=='SOURCE_REVIEW' and x['eventDate'] is None and x['status']=='BLOCKED' for x in read(c,r)['items'])


def test_missing_original_booking_evidence_blocks_without_zero(option_context):
 c,r,node,trade,execute,kind=option_context
 source=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
 c.execute(m.trade.insert().values(**(source|dict(trade_id=uuid4()))))
 rows=read(c,r)['items'];assert rows and all(x['status']=='BLOCKED' and not x['positionAssessed'] and x['remainingEntries'] is None for x in rows)


def test_read_only_scope_and_disabled_notification_are_rechecked(option_context):
 from security_master_schema import access_management as am
 from lifecycle.worklist_options import inspect_option
 c,r,node,trade,execute,kind=option_context
 actor=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Option deadline reader')
 group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='OPT_READ_'+uuid4().hex,name='Selected option strategy',actions=['LIFECYCLE_READ'],scope_mode='SELECTED',strategy_ids=[r.strategy_id])
 am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],actor,[group])
 assert inspect_option(c,r.tenant_id,actor,r.strategy_id,node,'EXPIRY')['positionAssessed']
 with pytest.raises(PermissionError):inspect_option(c,r.tenant_id,actor,ids['uk_fund_strategy'],node,'EXPIRY')
 with pytest.raises(PermissionError):inspect_option(c,ids['second_tenant'],actor,r.strategy_id,node,'EXPIRY')
 configure(c,0,event='OPTION_EXPIRY',strategy=r.strategy_id)
 with pytest.raises(LookupError):inspect_option(c,r.tenant_id,actor,r.strategy_id,node,'EXPIRY')


def test_opposing_allocations_survive_zero_net(option_context):
 from tests.test_lifecycle_allocation_store import field
 from tests.profile_fixtures import configure_allocation,allocation_policy
 c,r,node,trade,execute,kind=option_context
 sale=execute('SELL','10')
 dimension=field(c,r.tenant_id)
 for identity,value in [(trade,'alpha'),(sale,'beta')]:c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
 configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Retain option allocations')
 rows=read(c,r)['items'];assert rows and all(x['remainingEntries']==2 and Decimal(x['quantities'][0]['netQuantity'])==0 and Decimal(x['quantities'][0]['grossQuantity'])==20 for x in rows)


def test_inaccessible_underlying_is_not_disclosed(option_context):
 from lifecycle.worklist_options import inspect_option
 c,r,node,trade,execute,kind=option_context
 underlying=c.scalar(select(m.option_terms.c.underlying_reference_node_id).where(m.option_terms.c.instrument_node_id==node,m.option_terms.c.is_current))
 scope=m.reference_node_scope
 current=c.execute(select(scope).where(scope.c.reference_node_id==underlying)).mappings().first()
 if current:c.execute(scope.update().where(scope.c.reference_node_id==underlying).values(scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
 else:c.execute(scope.insert().values(reference_node_id=underlying,scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant'],status='ACTIVE'))
 view=inspect_option(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,'EXPIRY')
 assert view['underlyingId'] is None and view['underlyingName'] is None
 assert all(x['status']=='BLOCKED' for x in read(c,r)['items'])


def test_option_downgrade_respects_notification_only_support(option_context):
 from lifecycle.assistance_transitions import preview_assistance_transition
 from lifecycle.entitlements import lifecycle_subscription_view
 c,r,node,trade,execute,kind=option_context
 request=dict(proposedMaximumTier=2,expectedSubscriptionRevision=lifecycle_subscription_view(c,r.tenant_id)['revision'],scope='SELECTED',targets=[(r.strategy_id,'OPTION_EXPIRY')],replacement='HIGHEST_AVAILABLE')
 view=preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request)
 assert view['items'][0]['afterTier']==1 and view['changedCount']==0
 with pytest.raises(ValueError,match='support level'):preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request|dict(scope='ALL_CONFIGURED',targets=[],replacement='EXPLICIT',targetTier=2))


@pytest.mark.parametrize('option_context',['physical'],indirect=True)
def test_complete_option_population_is_filtered_before_pagination(option_context):
 from tests.profile_fixtures import assign
 from lifecycle.assistance import append_selection
 c,r,node,trade,execute,kind=option_context
 source=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
 for number in range(26):
  target=uuid4()
  c.execute(m.strategy.insert().values(**(source|dict(strategy_id=target,strategy_code='OPT_PAGE_'+target.hex,display_name=f'Option deadline page {number:02d}'))))
  assign(c,r.tenant_id,ids['demo_user_account'],target)
  execute(strategy=target)
  append_selection(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],target,'OPTION_EXPIRY',1,0,'Synthetic option pagination')
 query=dict(strategyId=None,fromDate=date(2027,9,17),toDate=date(2027,9,17),q=str(node),limit=25)
 first=read(c,r,**query);second=read(c,r,**query,offset=25)
 assert first['total']==second['total']==54 and len(first['items'])==len(second['items'])==25
 assert sum(first['statusCounts'].values())==54
 assert not {x['eventKey'] for x in first['items']} & {x['eventKey'] for x in second['items']}
 assert read(c,r,**query,attention='ACTIONABLE')['total']==0
 from lifecycle.worklist_options import inspect_option
 row=second['items'][0]
 assert inspect_option(c,r.tenant_id,ids['demo_user_account'],row['strategyId'],node,row['milestoneKind'])['eventKey']==row['eventKey']

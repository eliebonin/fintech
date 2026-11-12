"""Coupon notifications are scoped source inspection, never financial commands."""
from uuid import uuid4
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup as bond_setup
from tests.test_lifecycle_worklist import read
from tests.test_bond_coupons import schedule_data,grant_coupon_ops
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from lifecycle import coupon_service,coupon_tables as ct
from lifecycle.coupon_contracts import ScheduleCreate,PaymentCreate

def setup(c,r,trade):
 bond_setup(c,r,trade);grant_coupon_ops(c,r.tenant_id,r.strategy_id)
 return coupon_service.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),str(uuid4()))

def test_coupon_query_and_review_states_are_explicit():
 from lifecycle.worklist_contracts import WorklistQuery
 assert WorklistQuery(fromDate='2026-10-01',toDate='2026-10-31',eventType='BOND_COUPON',status='REVIEW_DUE').eventType=='BOND_COUPON'

def test_scheduled_coupon_discovery_and_inspection_are_financially_inert(valued):
 from lifecycle.worklist_coupons import inspect_coupon
 from lifecycle.worklist_contracts import WorklistResponse
 from valuation import tables as vt
 c,r,trade=valued;schedule=setup(c,r,trade)
 counts=lambda:tuple(c.scalar(select(func.count()).select_from(t)) for t in [m.trade,m.cash_balance,vt.accrual_input,ct.payment])
 before=counts();result=WorklistResponse.model_validate(read(c,r,eventType='BOND_COUPON'))
 assert result.total==1;row=result.items[0]
 assert row.eventType=='BOND_COUPON' and row.status=='REVIEW_DUE' and row.attention=='ACTIONABLE'
 assert row.eventDate.isoformat()=='2026-10-01' and row.couponPeriodId==schedule['cashflows'][0]['cashflow_id']
 view=inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,row.couponPeriodId)
 assert view['amountPer100']=='1' and view['currency']=='GBP' and view['confirmations']==[]
 assert view['financialTreatment']=='NOT_ASSESSED' and 'expectedAmount' not in view
 assert counts()==before

def test_confirmations_and_reversals_do_not_imply_cash_or_income(valued):
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;schedule=setup(c,r,trade);period=schedule['cashflows'][0]['cashflow_id']
 receipt=coupon_service.record_payment(c,r.tenant_id,ids['demo_user_account'],PaymentCreate(strategyId=r.strategy_id,periodId=period,paymentDate='2026-10-01',amount='1000',currencyId=ids['gbp_currency'],sourceReference='Synthetic receipt only',note='May already be reflected in EoD balances',confirmPayment=True),str(uuid4()))
 row=read(c,r,eventType='BOND_COUPON')['items'][0]
 assert row['status']=='CONFIRMATION_RECORDED' and row['attention']=='INFORMATION'
 view=inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,period)
 assert view['confirmations'][0]['amount']=='1000' and view['financialTreatment']=='NOT_ASSESSED'
 coupon_service.reverse_payment(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,receipt['payment_id'],'Synthetic reversal',str(uuid4()))
 assert read(c,r,eventType='BOND_COUPON')['items'][0]['status']=='REVIEW_DUE'
 assert inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,period)['confirmations'][0]['status']=='REVERSED'


def test_only_stored_coupons_in_explicit_window_are_discovered(valued):
 c,r,trade=valued;setup(c,r,trade)
 assert read(c,r,eventType='BOND_COUPON',fromDate=__import__('datetime').date(2026,10,2),includeEarlierOverdue=True)['total']==0
 assert read(c,r,eventType='BOND_COUPON',offset=25)['total']==1
 assert read(c,r,eventType='BOND_COUPON',offset=25)['items']==[]

def test_earlier_schedule_confirmations_are_not_transferred_to_revision(valued):
 import pytest
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;old=setup(c,r,trade);period=old['cashflows'][0]['cashflow_id']
 coupon_service.record_payment(c,r.tenant_id,ids['demo_user_account'],PaymentCreate(strategyId=r.strategy_id,periodId=period,paymentDate='2026-10-01',amount='1000',currencyId=ids['gbp_currency'],sourceReference='Old schedule receipt',confirmPayment=True),str(uuid4()))
 current=coupon_service.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data(expectedRevision=1,reason='Revised source')),str(uuid4()))
 row=read(c,r,eventType='BOND_COUPON')['items'][0];assert row['status']=='REVIEW_DUE'
 view=inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,current['cashflows'][0]['cashflow_id'])
 assert len(view['confirmations'])==1 and view['confirmations'][0]['currentSchedule'] is False
 with pytest.raises(LookupError):inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,period)

def test_inspection_of_later_page_does_not_depend_on_first_page(valued):
 from datetime import date,timedelta
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;setup(c,r,trade)
 flows=[dict(cashflowKey=f'PERIOD_{i}',cashflowType='COUPON',accrualStart=(date(2020,1,1)+timedelta(days=i*30)).isoformat(),accrualEnd=(date(2020,1,1)+timedelta(days=(i+1)*30)).isoformat(),paymentDate='2026-10-01',amountPer100='1') for i in range(31)]
 coupon_service.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data(expectedRevision=1,reason='Sourced arrears periods',cashflows=flows)),str(uuid4()))
 result=read(c,r,eventType='BOND_COUPON',offset=25)
 assert result['total']==31 and len(result['items'])==6
 period=result['items'][-1]['couponPeriodId']
 assert inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,period)['periodId']==str(period)

def test_coupon_visibility_tracks_bond_notifications_without_new_grants(valued):
 import pytest
 from tests.test_lifecycle_assistance import configure
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;schedule=setup(c,r,trade)
 configure(c,1,strategy=r.strategy_id)
 assert read(c,r,eventType='BOND_COUPON')['items'][0]['selectedTier']==1
 configure(c,0,strategy=r.strategy_id)
 assert read(c,r,eventType='BOND_COUPON')['total']==0
 with pytest.raises(LookupError):inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,schedule['cashflows'][0]['cashflow_id'])
 with pytest.raises(PermissionError):inspect_coupon(c,ids['second_tenant'],ids['demo_user_account'],r.strategy_id,schedule['cashflows'][0]['cashflow_id'])


def test_read_only_actor_can_inspect_only_its_selected_strategy(valued):
 import pytest
 from security_master_schema import access_management as am
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;schedule=setup(c,r,trade)
 actor=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Synthetic coupon reader')
 group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='COUPON_READ_'+uuid4().hex,name='Read only coupon desk',actions=['LIFECYCLE_READ'],scope_mode='SELECTED',strategy_ids=[r.strategy_id])
 am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],actor,[group])
 period=schedule['cashflows'][0]['cashflow_id']
 assert inspect_coupon(c,r.tenant_id,actor,r.strategy_id,period)['periodId']==str(period)
 with pytest.raises(PermissionError):inspect_coupon(c,r.tenant_id,actor,ids['strategy'],period)


def test_principal_only_and_unknown_formula_amount_are_not_coupon_income(valued):
 from lifecycle.worklist_coupons import inspect_coupon
 c,r,trade=valued;setup(c,r,trade)
 coupon_service.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data(expectedRevision=1,reason='Principal-only schedule',cashflows=[dict(cashflowKey='PRINCIPAL',cashflowType='PRINCIPAL',paymentDate='2026-10-01',amountPer100='100')])),str(uuid4()))
 assert read(c,r,eventType='BOND_COUPON')['total']==0
 data=schedule_data(expectedRevision=2,reason='Sourced formula only')
 data['cashflows'][0].pop('couponRate');data['cashflows'][0].pop('amountPer100');data['cashflows'][0]['amountFormula']='Contractual index rate plus spread; amount not supplied'
 saved=coupon_service.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(data),str(uuid4()))
 view=inspect_coupon(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,saved['cashflows'][0]['cashflow_id'])
 assert view['amountPer100'] is None and view['couponRate'] is None and view['amountFormula']
 assert view['financialTreatment']=='NOT_ASSESSED'

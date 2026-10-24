"""Native booking import: signed source economics, traceability and safe replay."""
from datetime import date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select,func
import pytest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection
from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load


def test_native_request_preserves_signed_economics_and_truncates_not_rounds():
    from tooling.reconciliation_csv.reconciliation_postings import booking_request
    from types import SimpleNamespace
    row=dict(trade_id='source-1',quantity='-16.8467618260486',price='1.0409059999999999',
        trade_datetime_utc='2026-10-02 12:00:00',settlement_date='',trade_currency='GBP',trade_type='Investment',comment='source note')
    cv=SimpleNamespace(price_basis='SWAP_VALUE_PER_UNIT',quote_factor=Decimal(1),quantity_unit='UNITS')
    context=SimpleNamespace(kind='SWAP',currency='GBP',terms_fingerprint='a'*64,convention=cv)
    request,evidence=booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    assert request.side=='SELL' and request.quantity==Decimal('16.846761826048')
    assert request.execution_price==Decimal('1.040905999999')
    assert request.settlement_date is None
    assert evidence['quantity']['sourceValue']=='-16.8467618260486'
    assert Decimal(evidence['quantity']['delta'])==Decimal('0.0000000000006')
    row['quantity']='-123456789012345678.123456789012'
    precise,_=booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    assert precise.quantity==Decimal('123456789012345678.123456789012')
    row['trade_currency']='USD'
    with pytest.raises(ValueError,match='currency'):booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])


def test_amc_keeps_quantity_and_maximum_price_digits_compatible_with_native_consideration():
    from tooling.reconciliation_csv.reconciliation_postings import booking_request
    from types import SimpleNamespace
    row=dict(trade_id='amc',quantity='-1200092.9',price='0.9936969999999999',trade_currency='USD',
        trade_datetime_utc='2026-04-17 12:00:00',settlement_date='2026-04-20')
    context=SimpleNamespace(kind='ACTIVELY_MANAGED_CERTIFICATE',currency='USD',terms_fingerprint='a'*64,
        convention=SimpleNamespace(price_basis='UNIT_PRICE',quote_factor=Decimal(1),quantity_unit='UNITS'))
    request,evidence=booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    assert request.quantity==Decimal('1200092.9') and request.execution_price==Decimal('0.99369699999')
    assert evidence['price']['sourceValue']=='0.9936969999999999'
    assert evidence['price']['decimalPlaces']==11
    row.update(quantity='1234567890123456.123456789013',price='98.5')
    with pytest.raises(ValueError,match='material'):
        booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])


def test_import_books_once_retains_originals_and_refuses_cross_tenant(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from apps.reference_api.amc_contracts import AmcProposalRequest
    from tests.test_amc import draft
    from tooling.reconciliation_csv.reconciliation_postings import post_positions
    c=connection;bundle=load(sample(tmp_path));tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    data=draft();data['convention'].update(quantityMinimum='0.000000000001',quantityIncrement='0.000000000001')
    proposal=submit_proposal(c,tenant,actor,AmcProposalRequest.model_validate(data))
    node=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Synthetic import').reference_node_id
    before=c.scalar(select(func.count()).select_from(m.trade))
    args=(c,bundle,tenant,actor,foundation,{'10':node},{'21':ids['bank_a_organisation']},{})
    result=post_positions(*args)
    assert result['booked']==1 and result['failed']==0,result['rows']
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1
    trade=c.execute(select(m.trade).where(m.trade.c.strategy_id==foundation['strategyId'])).mappings().one()
    assert trade.quantity==Decimal('1234567890123456.123456789012')
    assert post_positions(*args)['replayed']==1
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1
    event=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='RECONCILIATION_TRADE_BOOKED')).mappings().one()
    assert event.details['originalRow']['price']=='100'
    assert event.details['sourceTradeId']=='open'
    from security_master_schema.tenant_workspace import TenantActionForbidden
    with pytest.raises(TenantActionForbidden):
        post_positions(c,bundle,uuid4(),actor,foundation,{'10':node},{'21':ids['bank_a_organisation']},{})
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1


def test_metadata_uses_approved_source_nodes_and_versioned_fractional_conventions(connection,tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_products import additional_bundle
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_products import seed_products,seed_additional
    from tooling.reconciliation_csv.reconciliation_postings import prepare_position_metadata
    from apps.reference_api.product_booking import CONVENTION
    c=connection;bundle=additional_bundle(tmp_path);tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    products=seed_products(c,bundle,tenant,actor,foundation)
    additional=seed_additional(c,bundle,tenant,actor,foundation)
    nodes,parties=prepare_position_metadata(c,bundle,tenant,actor,foundation)
    assert nodes['10']==products['swaps']['10'] and nodes['1857']==additional['certificates']['1857']
    assert set(parties)=={'21'}
    assert c.scalar(select(m.organisation.c.display_name).where(m.organisation.c.organisation_id==parties['21']))=='Unverified source company 21'
    rows=c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==nodes['10'])
        .order_by(m.instrument_booking_convention.c.version_no)).mappings().all()
    assert len(rows)==2
    assert CONVENTION.validate_json(rows[0]['convention_payload']).quantity_increment==1
    assert CONVENTION.validate_json(rows[1]['convention_payload']).quantity_increment==Decimal('0.000000000001')
    assert prepare_position_metadata(c,bundle,tenant,actor,foundation)==(nodes,parties)
    assert c.scalar(select(func.count()).select_from(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==nodes['10']))==2

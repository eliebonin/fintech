"""Paired source components join the existing retained daily ingestion boundary."""
from datetime import date,datetime,timezone
from decimal import Decimal as D
import pytest
from market_data.contracts import DailyPoint,ParsedDelivery,ProviderSpec
from market_data.bond_quotes import BondQuoteAccrual
from market_data.ingestion import validate_normalized

STAMP=datetime(2026,10,5,21,tzinfo=timezone.utc)


def point(**changes):
    return DailyPoint(**(dict(field='PX_DIRTY',market_date=STAMP.date(),observed_at=STAMP,value=D('101'),value_basis='RAW',series_type='CLOSE',
        bond_price_type='DIRTY',bond_quote_accrual=BondQuoteAccrual(D(1),date(2026,10,7),'Synthetic paired source'))|changes))


def validate(p):
    validate_normalized(ParsedDelivery((p,),(),'RAW','EXCHANGE_CLOSE'),ProviderSpec('SYNTHETIC',('CLOSE',),10000,10),STAMP.date(),STAMP.date(),STAMP)


def test_optional_quote_package_is_typed_and_signed():
    validate(point())
    validate(point(bond_quote_accrual=BondQuoteAccrual(D('-.1'),date(2026,10,7),'Synthetic ex-coupon source')))
    validate(point(bond_quote_accrual=None)) # A DIRTY observation may be retained without being valuation-ready.


@pytest.mark.parametrize('change',[{'bond_price_type':'OTHER'},{'bond_price_type':'CLEAN'},{'value_basis':'SPLIT_ADJUSTED'},
    {'bond_quote_accrual':BondQuoteAccrual(D(1),date(2026,10,4),'Wrong quote date')},
    {'bond_quote_accrual':BondQuoteAccrual(D(1),date(2026,10,7),' ')}])
def test_invalid_source_package_is_rejected_before_publication(change):
    with pytest.raises(ValueError):validate(point(**change))


def test_atomic_quote_ingestion_replay_and_component_only_correction(connection):
    import json
    from dataclasses import replace
    from uuid import uuid4
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_market_data_ingestion import setup_dataset
    from market_data.ingestion import ingest_delivery
    from market_data.bond_quote_store import load_quote_accruals
    c=connection;dataset,namespace,original=setup_dataset(c)
    listing=uuid4();source=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==original)).mappings().one())
    c.execute(m.financial_reference_node.insert().values(**(source|dict(reference_node_id=listing,internal_code='QUOTE_'+listing.hex,canonical_name='Synthetic quote bond listing'))))
    source=dict(c.execute(select(m.listing).where(m.listing.c.listing_node_id==original)).mappings().one())
    c.execute(m.listing.insert().values(**(source|dict(listing_node_id=listing,instrument_node_id=ids['bond_instrument_node'],trading_symbol='QBOND',quote_factor=100,unit_multiplier=1))))
    c.execute(m.external_object_mapping.update().where(m.external_object_mapping.c.external_id_namespace_id==namespace).values(target_object_id=listing))
    def parse(payload,**_):
        points=tuple(DailyPoint('PX_DIRTY',date.fromisoformat(row['day']),datetime.fromisoformat(row['day']+'T21:00:00+00:00'),D(row['dirty']),'RAW','CLOSE',
            bond_price_type='DIRTY',bond_quote_accrual=BondQuoteAccrual(D(row['accrued']),date.fromisoformat(row['settlement']),'Synthetic paired provider')) for row in payload['quotes'])
        return ParsedDelivery(points,(),'RAW','EXPLICIT_UTC_EOD')
    raw=dict(quotes=[dict(day='2026-10-05',dirty='101',accrued='1',settlement='2026-10-07'),dict(day='2026-10-06',dirty='101.02',accrued='1.02',settlement='2026-10-08')])
    def ingest(key):return ingest_delivery(c,provider=ProviderSpec('SYNTHETIC_BOND',('CLOSE',),10000,10),parser=parse,
        dataset_id=dataset,namespace_id=namespace,symbol='AAPL',raw_payload=json.dumps(raw),delivery_key=key,
        received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),start=date(2026,10,5),end=date(2026,10,6))
    assert ingest('bond-1')['accepted']==2
    assert ingest('bond-1')['replayed'] is True
    assert ingest('bond-2')['duplicates']==2
    raw['quotes'][1]['accrued']='1.03'
    result=ingest('bond-3');assert result['accepted']==1 and result['duplicates']==1
    observations=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id==dataset)).mappings().all()
    assert len(observations)==3
    correction=next(row for row in observations if row['supersedes_observation_id'])
    predecessor=next(row for row in observations if row['market_data_observation_id']==correction['supersedes_observation_id'])
    assert correction['value']==predecessor['value']==D('101.02')
    components=load_quote_accruals(c,[row['market_data_observation_id'] for row in observations])
    assert components[predecessor['market_data_observation_id']]['accrued_interest_per_100']==D('1.02')
    assert components[correction['market_data_observation_id']]['accrued_interest_per_100']==D('1.03')


# The shared fixture enforces an owned disposable database and rolls back.
from tests.test_cash_booking_integrity import connection

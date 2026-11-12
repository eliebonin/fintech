from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.allocation_contracts import AllocationPolicy,FieldRule
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_lifecycle_allocation_store import field
from tests.test_structured_batch_reads import QueryCounter


def test_annotation_subsets_preserve_standard_fields_and_isolate_ambiguity(valued):
 from trading.annotation_snapshots import TradeAnnotationBatch,load_trade_annotations
 c,r,first=valued
 row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==first)).mappings().one());second=uuid4();c.execute(m.trade.insert().values(**(row|dict(trade_id=second))))
 a,b=field(c,r.tenant_id),field(c,r.tenant_id)
 canonical,comment,party=uuid4(),uuid4(),uuid4()
 policy=AllocationPolicy(fields=(FieldRule(canonical,'ALLOCATION',source_definition_ids=(a,b)),FieldRule(comment,'INHERIT',standard_field_key='COMMENT'),FieldRule(party,'ALLOCATION',standard_field_key='COUNTERPARTY')))
 c.execute(m.trade.update().where(m.trade.c.trade_id==first).values(comment='Retained standard note'))
 c.execute(m.trade_party_role.insert().values(trade_id=first,role='COUNTERPARTY',organisation_id=ids['bank_a_organisation']))
 for trade,x,y in [(first,'same','same'),(second,'one','two')]:
  for definition,value in [(a,x),(b,y)]:c.execute(m.trade_property_value.insert().values(trade_id=trade,tenant_id=r.tenant_id,definition_id=definition,value=value))
 expected=load_trade_annotations(c,r.tenant_id,[first],policy)
 source=TradeAnnotationBatch(c,r.tenant_id,[first,second],policy)
 with QueryCounter(c) as reads:
  assert source.for_trades(c,r.tenant_id,[first])==expected
  with pytest.raises(ValueError,match='ambiguous'):source.for_trades(c,r.tenant_id,[second])
 assert reads.count==0
 assert source.for_trades(c,r.tenant_id,[first])[first][comment].value=='Retained standard note'
 assert source.for_trades(c,r.tenant_id,[first])[first][party].value==str(ids['bank_a_organisation'])
 with pytest.raises(ValueError):source.for_trades(c,ids['second_tenant'],[first])
 with pytest.raises(ValueError):source.for_trades(c,r.tenant_id,[uuid4()])

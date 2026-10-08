"""Mark requirements and exact grouped bridge, not per-trade accounting."""
from datetime import timedelta
from decimal import Decimal as D
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import required_marks,attribute_projection,MarkKey

def test_closed_round_trip_needs_no_market_marks():
    p=reconstruct([booked(1,'2',OPEN+timedelta(hours=1)),booked(2,'-2',CLOSE,'110')],request())
    assert required_marks(p)==()
    result=attribute_projection(p,{},CURRENCY)
    assert result.market_pnl==20
    assert result.opening_value==result.closing_value==0
    assert result.execution_value==-20
    assert result.lines[0].attribution.components()=={'PRICE':D(20),'FX':D(0),'PRICE_FX_CROSS':D(0)}

def test_reopening_keeps_round_trip_and_only_needs_closing_mark():
    p=reconstruct([booked(1,'2',OPEN+timedelta(hours=1)),booked(2,'-2',OPEN+timedelta(hours=2),'110'),
                   booked(3,'4',CLOSE,'105')],request())
    requirements=required_marks(p)
    assert len(requirements)==1 and requirements[0].key.cutoff==CLOSE
    result=attribute_projection(p,{requirements[0].key:D(120)},CURRENCY)
    assert result.market_pnl==80 and result.execution_value==400

def test_flat_old_position_needs_no_marks_or_lines():
    p=reconstruct([booked(1,'5',OPEN-timedelta(days=2)),booked(2,'-5',OPEN-timedelta(days=1))],request())
    assert required_marks(p)==()
    r=attribute_projection(p,{},CURRENCY)
    assert r.lines==() and r.market_pnl==0

def test_opening_holding_partial_sale_bridge_and_required_marks():
    p=reconstruct([booked(1,'10',OPEN),booked(2,'-4',CLOSE,'110')],request())
    with pytest.raises(ValueError,match='Missing'):
        attribute_projection(p,{},CURRENCY)
    marks={MarkKey(p.buckets[0].key.subject_id,OPEN):D(100),MarkKey(p.buckets[0].key.subject_id,CLOSE):D(120)}
    r=attribute_projection(p,marks,CURRENCY)
    assert (r.opening_value,r.closing_value,r.execution_value,r.market_pnl)==(1000,720,-440,160)

@pytest.mark.parametrize('quantities',[('10','-4'),('-3','5'),('0.003','-0.001')])
def test_v2_bridge_matches_frozen_v1_reference_on_compatible_inputs(quantities):
    from tests import legacy_valuation_positions as old
    facts=[booked(1,quantities[0],OPEN),booked(2,quantities[1],CLOSE,'110')]
    p=reconstruct(facts,request())
    marks={MarkKey(p.buckets[0].key.subject_id,OPEN):D(100),MarkKey(p.buckets[0].key.subject_id,CLOSE):D(120)}
    new=attribute_projection(p,marks,CURRENCY)
    events=[]
    for f in facts:
        b=f.booking
        lot=old.BookedLot(b.trade_id,b.subject_id,b.quantity,b.price,b.currency_id,b.quantity_unit,b.unit_multiplier,b.quote_factor,f.effective_at)
        events.append(old.BookingEvent(f.event_id,f.trade_id,1,'BOOKED',f.effective_at,f.recorded_at,lot))
    previous=old.attribute_period(events,OPEN,CLOSE,request().information_cutoff,
        {p.buckets[0].key.subject_id:old.PeriodMarks(D(100),D(120),D(1),D(1))},
        execution_fx={f.trade_id:D(1) for f in facts})
    assert (new.market_pnl,new.opening_value,new.closing_value,new.execution_value)==(
        previous.market_pnl,previous.opening_value,previous.closing_value,previous.execution_value)

"""Exact chart summaries, independent of paged movement presentation."""
from datetime import datetime,timezone,timedelta
from positions.chart import movement_chart

DAY=datetime(2026,9,1,10,tzinfo=timezone.utc)
def item(n,quantity,running,source='BOOKED_TRADE',instant=DAY,ratio=None):
    return dict(movementId=str(n),effectiveAt=instant,quantity=quantity,runningQuantity=running,source=source,ratio=ratio)

def test_same_instant_buys_and_sells_remain_visible_even_when_net_flat():
    points=movement_chart([item(1,'100','100'),item(2,'-100','0')])
    assert len(points)==1
    assert points[0]['buyQuantity']=='100' and points[0]['sellQuantity']=='-100'
    assert points[0]['runningQuantity']=='0' and points[0]['tradeCount']==2

def test_split_is_not_a_trade_and_decimal_labels_stay_exact():
    points=movement_chart([item(1,'0.000000000001','0.000000000001'),
        item(2,'0.000000000001','0.000000000002','REVIEWED_CORPORATE_ACTION',DAY+timedelta(days=1),'2')])
    assert points[0]['buyQuantity']=='0.000000000001'
    assert points[1]['buyQuantity']=='0' and points[1]['tradeCount']==0
    assert points[1]['splitQuantity']=='0.000000000001' and points[1]['splitRatios']==['2']

def test_full_series_keeps_shorts_and_closing_reopened_episodes():
    points=movement_chart([item(1,'10','10'),item(2,'-15','-5',instant=DAY+timedelta(days=1)),
        item(3,'5','0',instant=DAY+timedelta(days=2)),item(4,'7','7',instant=DAY+timedelta(days=3))])
    assert [p['runningQuantity'] for p in points]==['10','-5','0','7']
    assert movement_chart([])==[]

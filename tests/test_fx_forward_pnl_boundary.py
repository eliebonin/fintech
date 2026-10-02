import pytest
from tests.test_fx_forward_booking_api import instrument,payload,request
from security_master_schema.demo_data import DEMO_IDS
from sqlalchemy import select,update
from apps.reference_api.db import get_engine
from security_master_schema import models as m

def test_mixed_strategy_never_returns_a_partial_cash_pnl(instrument):
    booked=request("POST","/v1/trades/fx-forwards",payload(instrument))
    assert booked.status_code==201,booked.text
    with get_engine().connect() as c:
        code=c.scalar(select(m.strategy.c.strategy_code).where(m.strategy.c.strategy_id==DEMO_IDS["strategy"]))
    response=request("GET",f"/v1/portfolios/{code}/pnl?asOfDate=2026-10-01")
    assert response.status_code==422,response.text
    assert response.json()["code"]=="valuation.fx_forward_unsupported"
    assert "data" not in response.json()

def test_future_fx_does_not_block_prior_cash_asof(instrument):
    with get_engine().connect() as c:
        code=c.scalar(select(m.strategy.c.strategy_code).where(m.strategy.c.strategy_id==DEMO_IDS["strategy"]))
    response=request("GET",f"/v1/portfolios/{code}/pnl?asOfDate=2026-08-28")
    assert response.status_code==200,response.text

@pytest.mark.parametrize("cancelled",[False,True])
def test_forward_only_guard_precedes_any_scalar_valuation(instrument,monkeypatch,cancelled):
    from uuid import uuid4
    from datetime import date
    from apps.reference_api import repository
    from apps.reference_api.fx_forward_booking import FxForwardValuationUnsupported
    from tests.test_fx_forward_booking_api import direct_payload,direct_book
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            strategy=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==DEMO_IDS["strategy"])).mappings().one())
            strategy.update(strategy_id=uuid4(),strategy_code=f"FX_ONLY_{uuid4().hex}")
            c.execute(m.strategy.insert().values(**strategy))
            data=direct_payload(c,instrument,strategyId=str(strategy["strategy_id"]))
            detail=direct_book(c,data)
            if cancelled:
                c.execute(update(m.trade).where(m.trade.c.trade_id==detail.data.trade.trade_id).values(lifecycle_status="CANCELLED"))
                result=repository.portfolio_pnl(c,DEMO_IDS["tenant"],strategy["strategy_code"],date(2026,10,1),"v1","fx-test")
                assert result is not None
            else:
                monkeypatch.setattr(repository,"_latest_observation",lambda *a,**k:pytest.fail("FX must be rejected before scalar price valuation"))
                with pytest.raises(FxForwardValuationUnsupported) as error:repository.portfolio_pnl(c,DEMO_IDS["tenant"],strategy["strategy_code"],date(2026,10,1),"v1","fx-test")
                assert error.value.trade_ids==(detail.data.trade.trade_id,)
        finally:tx.rollback()

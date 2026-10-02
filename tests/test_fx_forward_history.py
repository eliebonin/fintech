from decimal import Decimal
from uuid import UUID
from sqlalchemy import update
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from tests.test_fx_forward_booking_api import instrument, payload, request

def test_snapshot_survives_term_changes_and_is_visible_in_history(instrument):
    booked=request("POST","/v1/trades/fx-forwards",payload(instrument,quantity="0.000001"))
    assert booked.status_code==201,booked.text
    trade=booked.json()["data"]["trade"]
    with get_engine().begin() as connection:
        original=connection.execute(m.fx_forward_terms.select().where(m.fx_forward_terms.c.instrument_node_id==UUID(instrument))).mappings().one()
        connection.execute(update(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id==UUID(instrument)).values(agreed_forward_rate=Decimal("1.25")))
    try:
        detail=request("GET",f"/v1/trades/{trade['tradeId']}")
        assert detail.status_code==200
        assert detail.json()["data"]["trade"]["fxForwardEconomics"]==trade["fxForwardEconomics"]
        history=request("GET","/v1/trades?fromDate=2026-10-01&toDate=2026-10-01&limit=100")
        found=next(t for t in history.json()["data"] if t["tradeId"]==trade["tradeId"])
        assert found["listingId"] is None
        assert Decimal(found["quantity"])==Decimal("0.000001")
        assert found["fxForwardEconomics"]["payAmount"]=="0.0000011"
        assert request("GET",f"/v1/trades/{trade['tradeId']}",tenant="second_tenant").status_code in (403,404)
    finally:
        with get_engine().begin() as connection:
            connection.execute(update(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id==UUID(instrument)).values(agreed_forward_rate=original["agreed_forward_rate"]))

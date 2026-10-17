"""Only the identified synthetic workaround may be replaced, never real trades."""
from datetime import datetime,date,timezone
from decimal import Decimal
import pytest


def records():
    from scripts.restore_air_liquide_replay_fixture import ORIGINAL,CURRENT,ACTOR,LISTING,STRATEGY
    common=dict(booked_by_user_account_id=ACTOR,trade_subject_reference_node_id=LISTING,strategy_id=STRATEGY,
        comment='SYNTHETIC UI ACCEPTANCE ONLY. Explicit mock scenario.',quantity=Decimal(100),
        execution_price=Decimal('180'),settlement_date=date(2024,10,17),
        trade_datetime_utc=datetime(2024,10,15,18,tzinfo=timezone.utc))
    return common|dict(trade_id=ORIGINAL,lifecycle_status='SUPERSEDED'),common|dict(trade_id=CURRENT,lifecycle_status='BOOKED')


def test_replacement_preserves_original_economics_and_links_active_workaround():
    from scripts.restore_air_liquide_replay_fixture import replacement_payload,CURRENT
    original,current=records()
    payload=replacement_payload(original,current,2,[])
    assert payload['quantity']=='100' and payload['executionPrice']=='180'
    assert payload['tradeDatetime']=='2024-10-15T18:00:00+00:00'
    assert payload['correction']['tradeId']==str(CURRENT) and payload['correction']['expectedSequenceNo']==2


def test_real_or_changed_fixture_is_never_silently_corrected():
    from scripts.restore_air_liquide_replay_fixture import replacement_payload
    original,current=records()
    with pytest.raises(ValueError): replacement_payload(original,current|{'comment':'Real trade'},2,[])
    with pytest.raises(ValueError): replacement_payload(original,current|{'quantity':Decimal(200)},2,[])

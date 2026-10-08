from datetime import datetime, date, timezone
from decimal import Decimal
import pytest

from security_master_schema.fx_delivery import DeliveryError, DeliveryRecord, replay_delivery

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
DUE = date(2026, 10, 1)

def confirmation(sequence, leg, amount, at=NOW):
    return DeliveryRecord(sequence, 'CONFIRM', at, 'Synthetic custodian reference', leg, Decimal(amount))

def replay(records, due=DUE):
    return replay_delivery(Decimal('100'), Decimal('110'), due, records, now=NOW)

def test_expected_date_never_proves_delivery():
    assert replay([]).status == 'DUE'
    assert replay([], date(2026, 12, 15)).status == 'PENDING'

def test_partial_and_both_legs_are_required():
    first = replay([confirmation(2, 'RECEIVE', '40')])
    assert first.status == 'PARTIAL' and first.receive_outstanding == Decimal('60')
    assert first.pay_outstanding == Decimal('110')
    assert replay([confirmation(2,'RECEIVE','100')]).status == 'PARTIAL'
    assert replay([confirmation(2,'RECEIVE','100'), confirmation(3,'PAY','110')]).status == 'DELIVERED'

def test_reversal_reopens_only_target_leg_and_preserves_evidence():
    events = [confirmation(2,'RECEIVE','100'), confirmation(3,'PAY','110'),
        DeliveryRecord(4,'REVERSE',NOW,'Wrong reference',target_sequence=2)]
    result = replay(events)
    assert result.status == 'PARTIAL' and result.receive_outstanding == 100 and result.pay_outstanding == 0
    assert result.reversible_sequences == (3,)
    assert replay(events + [confirmation(5,'RECEIVE','100')]).status == 'DELIVERED'

@pytest.mark.parametrize('amount',['0','-1','NaN','Infinity','100.0000000000000000000000001'])
def test_invalid_confirmation_amount_is_refused(amount):
    with pytest.raises(DeliveryError): replay([confirmation(2,'RECEIVE',amount)])

def test_overdelivery_and_unknown_leg_are_refused():
    for events in [[confirmation(2,'PAY','111')], [confirmation(2,'OTHER','1')]]:
        with pytest.raises(DeliveryError): replay(events)

@pytest.mark.parametrize('at', [datetime(2026,9,30,tzinfo=timezone.utc), datetime(2026,10,7,tzinfo=timezone.utc), datetime(2026,10,2)])
def test_actual_delivery_requires_valid_past_effective_time(at):
    with pytest.raises(DeliveryError): replay([confirmation(2,'RECEIVE','1',at)])

def test_reversal_requires_existing_unreversed_confirmation_and_later_time():
    for records in [
        [DeliveryRecord(2,'REVERSE',NOW,'reason',target_sequence=1)],
        [confirmation(2,'PAY','10'),DeliveryRecord(3,'REVERSE',datetime(2026,10,1,tzinfo=timezone.utc),'reason',target_sequence=2)],
        [confirmation(2,'PAY','10'),DeliveryRecord(3,'REVERSE',NOW,'reason',target_sequence=2),DeliveryRecord(4,'REVERSE',NOW,'reason',target_sequence=2)],
    ]:
        with pytest.raises(DeliveryError): replay(records)

def test_blank_evidence_unknown_actions_and_unordered_sequences_fail_closed():
    for records in [[DeliveryRecord(2,'CONFIRM',NOW,' ', 'PAY', Decimal('1'))],
        [DeliveryRecord(2,'SETTLED',NOW,'reference')],
        [confirmation(3,'PAY','1'),confirmation(2,'PAY','1')]]:
        with pytest.raises(DeliveryError): replay(records)

def test_large_fractional_obligation_is_not_rounded_during_replay():
    exact=Decimal('123456789012345678901234567890123456789.123456789012345678901234')
    result=replay_delivery(exact,Decimal('1'),DUE,[confirmation(2,'RECEIVE',str(exact))],now=NOW)
    assert result.receive_confirmed == exact and result.receive_outstanding == 0

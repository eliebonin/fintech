"""A contractual business day is an evidenced calendar day, not a weekday."""
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import update
from tests.test_access_management import connection
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def calendar(c, *, missing=False, sealed=True):
    identity=uuid4()
    # Tenant publication stores an immutable decision for each assessed day.
    days={'2026-12-25':{'status':'CLOSED','reason':'Christmas'},
          '2026-12-26':{'status':'CLOSED','reason':'Weekend'},
          '2026-12-27':{'status':'CLOSED','reason':'Weekend'},
          '2026-12-28':{'status':'CLOSED','reason':'Substitute holiday'},
          '2026-12-29':{'status':'OPEN','reason':'Business day'}}
    if missing: days.pop('2026-12-28')
    c.execute(m.market_calendar.insert().values(market_calendar_id=identity,tenant_id=ids['tenant'],
        calendar_code='PAYMENT_'+identity.hex,display_name='Synthetic payment calendar',
        timezone_name='Europe/London',calendar_kind='SETTLEMENT',sealed=sealed,
        coverage_from=date(2026,12,24),coverage_to=date(2026,12,29),definition_json={'days':days}))
    return identity


def test_payment_lag_skips_evidenced_weekday_holidays(connection):
    from apps.reference_api.structured_product_dependencies import contractual_payment_dates
    assert contractual_payment_dates(connection,ids['tenant'],calendar(connection),[date(2026,12,24)],1)=={
        date(2026,12,24):date(2026,12,29)}


@pytest.mark.parametrize('missing,sealed',[(True,True),(False,False)])
def test_unknown_or_unpublished_calendar_blocks_generation(connection,missing,sealed):
    from apps.reference_api.structured_product_dependencies import contractual_payment_dates
    with pytest.raises(ValueError):
        contractual_payment_dates(connection,ids['tenant'],calendar(connection,missing=missing,sealed=sealed),[date(2026,12,24)],1)

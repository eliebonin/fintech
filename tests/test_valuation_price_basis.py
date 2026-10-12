from decimal import Decimal as D
from datetime import date, datetime, timezone
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued, service


def test_verified_prices_are_consumed_without_changing_source_or_execution(valued):
    from market_data.price_basis_store import record_price_basis_proof
    c, request, trade = valued
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
        value_basis=None,price_requirement='AS_TRADED',allow_split_conversion=True))
    rows=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],
        m.market_data_observation.c.market_date==date(2026,10,1))).mappings().all()
    for row in rows:
        c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==row['market_data_observation_id']).values(
            value=550,value_basis='SPLIT_ADJUSTED'))
        record_price_basis_proof(c,row['market_data_observation_id'],dict(method='SPLIT_ONLY',complete=True,
            marketDate='2026-10-01',anchorDate='2026-10-02',coverageStart='2026-10-01',coverageEnd='2026-10-02',
            sourceReference='synthetic-only',splits=[dict(date='2026-10-02',numerator='2',denominator='1')]),
            datetime(2026,10,2,18,tzinfo=timezone.utc))
    result=service().calculate(c,request)
    assert result.period.market_pnl == D('109.877')
    assert result.evidence['selections'][0]['selected_value']=='550'
    assert result.evidence['selections'][0]['pricing_evidence']['priceBasis']['valuationValue']=='1100.000000000000'
    assert c.scalar(select(m.trade.c.execution_price).where(m.trade.c.trade_id==trade))==D('1.23')

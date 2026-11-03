"""Count immutable source revisions, including corrections with moved dates."""
from datetime import datetime,timezone
from sqlalchemy import select,func,values,column,DateTime,Date
from . import tables as t
from lifecycle import coupon_tables as ct


def _counts(tenant,strategy,closing,info):
    a=t.accrual_input;p=ct.payment;chain=p.alias('accrued_coupon_chain')
    daily=select(func.count()).where(a.c.tenant_id==tenant,a.c.strategy_id==strategy,
        a.c.value_date<=closing,a.c.recorded_at<=info).scalar_subquery()
    relevant=select(chain.c.logical_payment_id).where(chain.c.tenant_id==tenant,chain.c.strategy_id==strategy,
        chain.c.payment_date<=closing,chain.c.recorded_at<=info)
    coupons=select(func.count()).where(p.c.tenant_id==tenant,p.c.strategy_id==strategy,
        p.c.logical_payment_id.in_(relevant),p.c.recorded_at<=info).scalar_subquery()
    return daily,coupons


def capture_balance_sources(c,r):
    daily,coupons=c.execute(select(*_counts(r.tenant_id,r.strategy_id,r.closing_cutoff.date(),r.information_cutoff))).one()
    anchors,builds=c.execute(select(*_maintained_counts(r.tenant_id,r.strategy_id,r.closing_cutoff.date(),r.information_cutoff))).one()
    return dict(version=2,dailyRevisionCount=daily,couponRevisionCount=coupons,balanceInputRevisionCount=anchors,balanceBuildCount=builds,
        closingDate=r.closing_cutoff.date().isoformat(),informationCutoff=r.information_cutoff.isoformat())


def _maintained_counts(tenant,strategy,closing,info):
    from .balance_history_tables import balance_input as a,history_build as b,history_day as h
    return (select(func.count()).select_from(a).where(a.c.tenant_id==tenant,a.c.strategy_id==strategy,a.c.value_date<=closing,a.c.recorded_at<=info).scalar_subquery(),
        select(func.count()).select_from(b).where(b.c.tenant_id==tenant,b.c.strategy_id==strategy,b.c.from_date<=closing,b.c.information_cutoff<=info,
            b.c.build_id.in_(select(h.c.build_id))).scalar_subquery())


def balance_health_statuses(c,headers):
    states={};rows=[]
    for h in headers:
        source=h['summary'].get('accruedBalanceSource')
        if source is None:continue  # Existing results retain their prior contract.
        try:
            info=datetime.fromisoformat(source['informationCutoff'])
            if (source['version'] not in (1,2) or info.tzinfo is None or source['closingDate']!=h['value_date'].isoformat()
                or type(source['dailyRevisionCount']) is not int or type(source['couponRevisionCount']) is not int):raise ValueError()
            rows.append((h['batch_id'],h['tenant_id'],h['strategy_id'],h['value_date'],
                max(info,datetime.now(timezone.utc)),source['dailyRevisionCount'],source['couponRevisionCount'],source.get('balanceInputRevisionCount',0),source.get('balanceBuildCount',0)))
        except (KeyError,TypeError,ValueError):states[h['batch_id']]='UNKNOWN_LEGACY'
    if not rows:return states
    frozen=values(column('batch_id',t.batch.c.batch_id.type),column('tenant_id',t.batch.c.tenant_id.type),
        column('strategy_id',t.batch.c.strategy_id.type),column('closing',Date()),column('info',DateTime(timezone=True)),
        column('daily_count',t.accrual_input.c.revision.type),column('coupon_count',ct.payment.c.revision.type),
        column('anchor_count',t.accrual_input.c.revision.type),column('build_count',t.accrual_input.c.revision.type)).data(rows).cte('frozen_accrued_sources')
    daily,coupons=_counts(frozen.c.tenant_id,frozen.c.strategy_id,frozen.c.closing,frozen.c.info)
    anchors,builds=_maintained_counts(frozen.c.tenant_id,frozen.c.strategy_id,frozen.c.closing,frozen.c.info)
    for identity,changed in c.execute(select(frozen.c.batch_id,(daily!=frozen.c.daily_count)|(coupons!=frozen.c.coupon_count)|(anchors!=frozen.c.anchor_count)|(builds!=frozen.c.build_count))):
        states[identity]='REASSESSMENT_REQUIRED' if changed else 'CURRENT'
    return states


def balance_reassessment_predicate(batch):
    """Queue filtering uses source revisions before pagination/counts."""
    source=batch.c.summary['accruedBalanceSource']
    info=func.greatest(source['informationCutoff'].astext.cast(DateTime(timezone=True)),func.clock_timestamp())
    daily,coupons=_counts(batch.c.tenant_id,batch.c.strategy_id,batch.c.value_date,info)
    anchors,builds=_maintained_counts(batch.c.tenant_id,batch.c.strategy_id,batch.c.value_date,info)
    return source['version'].as_integer().in_([1,2])&((daily!=source['dailyRevisionCount'].as_integer())|(coupons!=source['couponRevisionCount'].as_integer())|
        (anchors!=func.coalesce(source['balanceInputRevisionCount'].as_integer(),0))|(builds!=func.coalesce(source['balanceBuildCount'].as_integer(),0)))

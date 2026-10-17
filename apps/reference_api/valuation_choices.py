"""Search/count/page/selected lookup share one authorization-filtered query."""
from sqlalchemy import select, func, or_, String
from security_master_schema import models as m
from security_master_schema.strategy_access import request_strategy_predicate, require_strategy_action


def option_choices(c, tenant, actor, kind, *, q='', limit=25, offset=0,
        selected_id=None, strategy_id=None, for_calculation=False):
    if kind == 'strategies':
        table = m.strategy
        identity = table.c.strategy_id
        columns = [identity.label('id'), table.c.display_name.label('label'),
            table.c.base_currency_id.label('currencyId'),
            ((table.c.status == 'ACTIVE') & request_strategy_predicate(c, tenant, 'VALUATION_RUN', identity)).label('canCalculate')]
        conditions = [table.c.tenant_id == tenant, request_strategy_predicate(c, tenant, 'VALUATION_READ', identity)]
        if for_calculation:
            conditions += [table.c.status == 'ACTIVE', request_strategy_predicate(c, tenant, 'VALUATION_RUN', identity)]
        search = or_(table.c.display_name.icontains(q, autoescape=True), table.c.strategy_code.icontains(q, autoescape=True))
        order = (table.c.display_name, identity)
    elif kind == 'policies':
        table = m.valuation_policy
        identity = table.c.valuation_policy_id
        label = table.c.display_name + ' · ' + table.c.policy_code + ' · v' + table.c.version_no.cast(String)
        columns = [identity.label('id'), label.label('label'), table.c.valuation_cut_id.label('cutId'), table.c.strategy_id.label('strategyId')]
        conditions = [table.c.tenant_id == tenant, table.c.status == 'ACTIVE',
            or_(table.c.strategy_id.is_(None), request_strategy_predicate(c, tenant, 'VALUATION_READ', table.c.strategy_id))]
        if strategy_id is not None:
            require_strategy_action(c, tenant, actor, 'VALUATION_READ', strategy_id)
            conditions.append(or_(table.c.strategy_id.is_(None), table.c.strategy_id == strategy_id))
        search = or_(table.c.display_name.icontains(q, autoescape=True), table.c.policy_code.icontains(q, autoescape=True))
        order = (table.c.display_name, table.c.policy_code, table.c.version_no.desc(), identity)
    else:
        table = m.currency
        identity = table.c.currency_id
        columns = [identity.label('id'), table.c.currency_code.label('label')]
        conditions = [table.c.status == 'ACTIVE']
        search = table.c.currency_code.icontains(q, autoescape=True)
        order = (table.c.currency_code, identity)
    base = select(*columns).where(*conditions)
    filtered = base.where(search) if q else base
    total = c.scalar(select(func.count()).select_from(filtered.subquery()))
    items = [dict(row) for row in c.execute(filtered.order_by(*order).limit(limit).offset(offset)).mappings()]
    selected = c.execute(base.where(identity == selected_id)).mappings().one_or_none() if selected_id else None
    return dict(items=items, total=total, limit=limit, offset=offset, selected=dict(selected) if selected else None)

"""Revalidate live dependencies before proposal replay and graph materialisation.

Manual/provider values remain operator assertions, not machine-verified quotes.
When market-data evidence is attached, its subject, date, units and exact value
must agree; a UUID's existence alone never proves a contractual initial fixing.
"""
from datetime import timedelta
from sqlalchemy import select

from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action, has_all_strategy_scope
from market_data.calendar_store import visible_calendar, calendar_days
from market_data.display_access import assert_dataset_display
from .booking_errors import InvalidWorkflowState, RepositoryNotFound
from .source_evidence import require_scoped_source_evidence

CONTRACTUAL_CALENDAR_KINDS = ('TRADING', 'SETTLEMENT', 'FIXING', 'HOLIDAY', 'CONTINUOUS_24X7')


def contractual_payment_dates(c, tenant, calendar_id, observations, lag):
    """Exclude the observation day; count only explicit OPEN calendar days.

    A zero lag means the explicit observation date, with no invented roll rule.
    Even long closures are bounded to one year; uncovered dates fail closed.
    """
    calendar = visible_calendar(c, tenant, calendar_id)
    if calendar is None:
        raise RepositoryNotFound('Contractual calendar is unavailable for this tenant')
    if calendar['calendar_kind'] not in CONTRACTUAL_CALENDAR_KINDS:
        raise InvalidWorkflowState('Calendar is not eligible for contractual dates')
    if not calendar['sealed']:
        raise InvalidWorkflowState('Payment generation requires a published sealed calendar version')
    if not 0 <= lag <= 30:
        raise InvalidWorkflowState('Payment lag must be between 0 and 30 business days')
    result = {}
    for observation in sorted(set(observations)):
        if lag == 0:
            result[observation] = observation
            continue
        remaining = lag
        start = observation + timedelta(days=1)
        for day in calendar_days(c, calendar, start, start + timedelta(days=365)):
            if day['status'] not in {'OPEN', 'CLOSED'}:
                raise InvalidWorkflowState(f"Payment calendar has no assessed coverage on {day['date']}")
            if day['status'] == 'OPEN':
                remaining -= 1
            if remaining == 0:
                result[observation] = day['date']
                break
        if remaining:
            raise InvalidWorkflowState('Payment lag exceeds one year of assessed calendar coverage')
    return result


def _observation(c, tenant, fixing, observation_id):
    observation = c.execute(select(m.market_data_observation).where(
        m.market_data_observation.c.market_data_observation_id == observation_id
    ).with_for_update(read=True)).mappings().one_or_none()
    if observation is None:
        raise RepositoryNotFound('Initial-fixing observation is unavailable')
    series = c.execute(select(m.market_data_series).where(
        m.market_data_series.c.market_data_series_id == observation['market_data_series_id']
    ).with_for_update(read=True)).mappings().one()
    # Check current display rights before examining/disclosing economic agreement.
    assert_dataset_display(c, tenant, {observation['dataset_id']}, series_contexts={
        (observation['dataset_id'], observation['market_data_series_id'])})
    expected_types = {'LEVEL': {'PRICE', 'INDEX_LEVEL'}, 'INDEX_POINTS': {'INDEX_LEVEL'}, 'FX_RATE': {'RATE'}}
    if (series['status'] != 'ACTIVE' or series['reference_node_id'] != fixing.reference_node_id
            or observation['market_date'] != fixing.fixing_date
            or observation['value'] != fixing.initial_fixing
            or observation['quality_status'] != 'ACCEPTED'
            or observation['value_basis'] != 'RAW'
            or series['value_type'] not in expected_types.get(fixing.fixing_basis, set())):
        raise InvalidWorkflowState('Initial fixing must match an accepted unadjusted observation: instrument, date, value and units')
    if c.scalar(select(m.market_data_observation.c.market_data_observation_id).where(
            m.market_data_observation.c.supersedes_observation_id == observation_id,
            m.market_data_observation.c.quality_status == 'ACCEPTED').limit(1)):
        raise InvalidWorkflowState('Initial-fixing observation has been superseded')
    if fixing.source_payload_id is not None and observation['source_payload_id'] != fixing.source_payload_id:
        raise InvalidWorkflowState('Initial-fixing source payload does not match the observation')
    return observation


def validate_structured_dependencies(c, tenant, actor, request):
    """No writes, no inferred grants; callers retain the enclosing transaction."""
    calendar = visible_calendar(c, tenant, request.calendar_id)
    if calendar is None:
        raise RepositoryNotFound('Contractual calendar is unavailable for this tenant')
    if calendar['calendar_kind'] not in CONTRACTUAL_CALENDAR_KINDS:
        raise InvalidWorkflowState('Calendar is not eligible for contractual dates')
    if not calendar['sealed']:
        raise InvalidWorkflowState('New contractual proposals require a published sealed calendar version')
    if request.payment_date_convention == 'CALENDAR_LAG':
        dates = contractual_payment_dates(c, tenant, request.calendar_id,
            [row.observation_date for row in request.rows], request.payment_lag_business_days)
        if any(row.payment_date != dates[row.observation_date] for row in request.rows):
            raise InvalidWorkflowState('Payment dates differ from the published calendar. Refresh the schedule or retain explicit dates with a documented exception.')
    require_scoped_source_evidence(c, tenant, request.source_system_id, request.source_payload_id)
    for fixing in request.underlyings:
        require_scoped_source_evidence(c, tenant,
            fixing.source_system_id or request.source_system_id,
            fixing.source_payload_id or request.source_payload_id)
        if fixing.fixing_source == 'DERIVED':
            raise InvalidWorkflowState('Derived initial fixings require a supported explicit derivation; use a reviewed manual value instead')
        observation = None
        if fixing.market_data_observation_id is not None:
            observation = _observation(c, tenant, fixing, fixing.market_data_observation_id)
        if fixing.market_data_resolution_snapshot_id is None:
            continue
        snapshot = c.execute(select(m.market_data_resolution_snapshot).where(
            m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id == fixing.market_data_resolution_snapshot_id,
            m.market_data_resolution_snapshot.c.tenant_id == tenant
        ).with_for_update(read=True)).mappings().one_or_none()
        if snapshot is None:
            raise RepositoryNotFound('Initial-fixing snapshot is unavailable')
        if snapshot['strategy_id'] is not None:
            require_strategy_action(c, tenant, actor, 'VALUATION_READ', snapshot['strategy_id'])
        elif snapshot['context_scope'] != 'SHARED' and not has_all_strategy_scope(c, tenant, actor, 'VALUATION_READ'):
            raise RepositoryNotFound('Initial-fixing snapshot is unavailable')
        items = c.execute(select(m.market_data_resolution_snapshot_item).where(
            m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id == fixing.market_data_resolution_snapshot_id,
            m.market_data_resolution_snapshot_item.c.subject_reference_node_id == fixing.reference_node_id,
            m.market_data_resolution_snapshot_item.c.status == 'SELECTED',
            m.market_data_resolution_snapshot_item.c.pricing_date_used == fixing.fixing_date,
            m.market_data_resolution_snapshot_item.c.selected_value == fixing.initial_fixing
        )).mappings().all()
        if len(items) != 1 or items[0]['market_data_observation_id'] is None:
            raise InvalidWorkflowState('Initial fixing requires one matching observed snapshot item, not an override or ambiguous selection')
        item = items[0]
        if observation is not None and item['market_data_observation_id'] != observation['market_data_observation_id']:
            raise InvalidWorkflowState('Initial-fixing observation and snapshot disagree')
        selected = _observation(c, tenant, fixing, item['market_data_observation_id'])
        if item['dataset_id'] != selected['dataset_id'] or item['market_data_series_id'] != selected['market_data_series_id']:
            raise InvalidWorkflowState('Initial-fixing snapshot provenance disagrees with its observation')

"""Read-only projection of current approved contractual facts, independent of booking."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from security_master_schema import models as m
from .product_booking import require_visible
from .repository import RepositoryNotFound


class TermsLayer(BaseModel):
    instrumentId: str
    canonicalName: str
    instrumentType: str
    relation: str
    version: int
    issuer: str | None
    currency: str | None
    dates: dict
    economics: dict
    facts: dict[str, list[dict]]


class TermsScheduleView(BaseModel):
    instrumentId: str
    basis: str = 'CURRENT_APPROVED_TERMS'
    layers: list[TermsLayer]
    referenceLabels: dict[str, str]


class TermsScheduleResponse(BaseModel):
    data: TermsScheduleView


def _display(value):
    # Monetary levels must never travel through a binary float.
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, (UUID, date, datetime)): return str(value)
    if isinstance(value, dict): return {k: _display(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_display(v) for v in value]
    return value


def load_terms_schedule(c, tenant, instrument_id):
    layers, labels, visited = [], {}, set()

    def rows(table, predicate):
        return [dict(r) for r in c.execute(select(table).where(predicate).order_by(*table.primary_key.columns)).mappings()]

    def visible(node_id):
        node = require_visible(c, tenant, node_id)
        labels[str(node_id)] = node['canonical_name']
        return node

    def visit(node_id, relation, depth=0):
        if node_id in visited or depth > 3:
            raise RepositoryNotFound('Contractual reference chain cannot be displayed.')
        visited.add(node_id)
        node = visible(node_id)
        if depth and c.scalar(select(m.reference_node_type.c.type_code).where(m.reference_node_type.c.reference_node_type_id == node['reference_node_type_id'])) != 'INSTRUMENT':
            return  # An index/rate reference has no instrument contractual schedule.
        definitions = rows(m.instrument_definition_version,
            (m.instrument_definition_version.c.instrument_node_id == node_id)
            & m.instrument_definition_version.c.is_current
            & (m.instrument_definition_version.c.status == 'APPROVED'))
        if len(definitions) != 1: raise RepositoryNotFound('Current approved instrument terms unavailable.')
        definition = definitions[0]
        kind = c.scalar(select(m.instrument_type.c.type_code).where(m.instrument_type.c.instrument_type_id == definition['instrument_type_id']))
        if kind not in {'SWAP', 'STRUCTURED_PRODUCT'}:
            if depth: return
            raise RepositoryNotFound('Terms and schedule are supported for structured products and swaps.')
        issuer = c.scalar(select(m.organisation.c.legal_name).where(m.organisation.c.organisation_id == definition['issuer_organisation_id']))
        currency = c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id == definition['base_currency_id']))
        dates = rows(m.instrument_dates, m.instrument_dates.c.instrument_node_id == node_id)
        facts = {}
        economics = {}
        dependencies = []
        owners = {node_id}
        if kind == 'SWAP':
            generic = rows(m.swap_definition_version, m.swap_definition_version.c.instrument_definition_version_id == definition['instrument_definition_version_id'])
            economics = generic[0]['economics_payload'] if generic else {}
            facts['swapTerms'] = rows(m.swap_terms, m.swap_terms.c.instrument_node_id == node_id)
            facts['swapLegs'] = rows(m.swap_leg, m.swap_leg.c.swap_instrument_node_id == node_id)
            for leg in facts['swapLegs']:
                if leg['reference_node_id']:
                    visible(leg['reference_node_id'])
                    if leg['leg_role'] == 'PERFORMANCE': dependencies.append((leg['reference_node_id'], 'Swap performance reference'))
        else:
            terms = rows(m.structured_product_terms, (m.structured_product_terms.c.instrument_node_id == node_id)
                & m.structured_product_terms.c.is_current & m.structured_product_terms.c.status.in_(['ACTIVE', 'VALIDATED']))
            if len(terms) != 1: raise RepositoryNotFound('Current validated structured terms unavailable.')
            t = terms[0]['structured_product_terms_id']
            economics = terms[0]
            for key, table in [('initialFixings', m.structured_product_initial_fixing), ('conditions', m.structured_product_condition_group),
                ('couponProgrammes', m.structured_product_coupon_programme), ('rangeAccrual', m.structured_product_range_accrual_terms), ('supertracker', m.structured_product_supertracker_terms)]:
                facts[key] = rows(table, table.c.structured_product_terms_id == t)
            composition = rows(m.instrument_composition, m.instrument_composition.c.structured_product_terms_id == t)
            facts['composition'] = composition
            owners.update(row['component_reference_node_id'] for row in composition)
            facts['componentTerms'] = rows(m.structured_product_component_terms,
                m.structured_product_component_terms.c.instrument_composition_id.in_([r['instrument_composition_id'] for r in composition]))
            facts['optionTerms'] = rows(m.option_terms, m.option_terms.c.instrument_node_id.in_(owners)
                & m.option_terms.c.is_current & m.option_terms.c.status.in_(['ACTIVE','VALIDATED']))
            groups = [r['condition_group_id'] for r in facts['conditions']]
            facts['barriers'] = rows(m.barrier_rule, m.barrier_rule.c.condition_group_id.in_(groups))
            facts['actions'] = rows(m.condition_group_action, m.condition_group_action.c.condition_group_id.in_(groups))
            facts['couponPeriods'] = rows(m.structured_product_coupon_period,
                m.structured_product_coupon_period.c.coupon_programme_id.in_([r['coupon_programme_id'] for r in facts['couponProgrammes']]))
            wrapper = rows(m.structured_product_wrapper_terms, m.structured_product_wrapper_terms.c.structured_product_terms_id == t)
            if wrapper:
                economics = {**economics, **wrapper[0]['note_inputs_json'], 'transferTerms': wrapper[0]['transfer_terms_json']}
                dependencies.append((wrapper[0]['preference_share_instrument_id'], 'Linked preference share'))
            share = rows(m.preference_share_terms, m.preference_share_terms.c.structured_product_terms_id == t)
            if share:
                economics = {**economics, **share[0]['inputs_json']}
                pref_id = share[0]['preference_share_terms_id']
                facts['shareCalls'] = rows(m.preference_share_redemption_period, m.preference_share_redemption_period.c.preference_share_terms_id == pref_id)
                facts['terminalBranches'] = rows(m.preference_share_terminal_branch, m.preference_share_terminal_branch.c.preference_share_terms_id == pref_id)
        # Resolve explicit schedules referenced by component/group/action rows as well as owned schedules.
        schedule_ids, event_ids = set(), set()
        for entries in facts.values():
            for row in entries:
                for key, value in row.items():
                    if value is None: continue
                    if key in {'schedule_id', 'payment_schedule_id', 'observation_schedule_id'}: schedule_ids.add(value)
                    if key in {'schedule_event_id', 'observation_event_id'}: event_ids.add(value)
                    if key in {'component_reference_node_id', 'underlying_reference_node_id', 'target_reference_node_id', 'reference_node_id', 'owner_reference_node_id'}: visible(value)
        schedule_ids.update(c.scalars(select(m.schedule_event.c.schedule_id).where(m.schedule_event.c.schedule_event_id.in_(event_ids))))
        schedules = rows(m.schedule, m.schedule.c.owner_reference_node_id.in_(owners) | m.schedule.c.schedule_id.in_(schedule_ids))
        for row in schedules: visible(row['owner_reference_node_id'])
        facts['scheduleEvents'] = rows(m.schedule_event, m.schedule_event.c.schedule_id.in_([r['schedule_id'] for r in schedules]))
        facts['scheduleEvents'].sort(key=lambda row: (row['event_date'], row['event_sequence'], str(row['schedule_event_id'])))
        # Attach schedule purpose so the UI can distinguish observation, reset and payment rows.
        by_schedule = {r['schedule_id']: r['schedule_type'] for r in schedules}
        for row in facts['scheduleEvents']: row['schedule_type'] = by_schedule[row['schedule_id']]
        layers.append(TermsLayer(instrumentId=str(node_id), canonicalName=node['canonical_name'], instrumentType=kind,
            relation=relation, version=definition['sequence_no'], issuer=issuer, currency=currency,
            dates=_display(dates[0] if dates else {}), economics=_display(economics), facts=_display(facts)))
        for dependency, label in dependencies: visit(dependency, label, depth + 1)

    visit(instrument_id, 'Selected instrument')
    return TermsScheduleView(instrumentId=str(instrument_id), layers=layers, referenceLabels=labels)

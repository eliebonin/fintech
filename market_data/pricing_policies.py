"""Governed policy commands and definitions; no HTTP or engine ownership.

Callers own the Connection and atomic commit/audit. Creation checks current
authority before retry lookup; all request fingerprints and lock keys remain
unchanged. The definition loader is an internal projection, not an auth endpoint.
"""
from copy import deepcopy
import hashlib
import json
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.engine import Connection
from security_master_schema import models as m
from security_master_schema.errors import IdempotencyKeyConflict, RepositoryNotFound
from security_master_schema.governance_clock import governance_date
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.market_data_visibility import catalogue_subject_clause
from .closing_prices import close_type
from .pricing_policy_contracts import PolicyCreate, PolicyDefinition, PolicyRuleInput


def authority(c,tenant,actor,write=False):
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    if 'MARKET_DATA' not in workspace.module_codes or (write and 'MARKET_DATA_MANAGE' not in workspace.permission_codes):
        raise PermissionError('Active MARKET_DATA membership' + (' and tenant administrator' if write else '') + ' required')
    return 'MARKET_DATA_MANAGE' in workspace.permission_codes


def policy_definition(c: Connection,tenant: UUID,policy_id: UUID) -> PolicyDefinition:
    """Internal projection after caller authority; retain bound strategy checks."""
    row=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==tenant,
        m.valuation_policy.c.valuation_policy_id==policy_id)).mappings().one_or_none()
    if not row:
        raise RepositoryNotFound('Policy not found')
    if row['strategy_id'] and c.info.get('request_actor'):
        require_strategy_action(c,tenant,c.info['request_actor'],
            'STRATEGY_WRITE' if c.info.get('request_action')=='MARKET_DATA_MANAGE' else 'STRATEGY_READ',row['strategy_id'])
    rules=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_id==policy_id).order_by(
        m.valuation_policy_rule.c.rule_sequence)).mappings().all()
    return PolicyDefinition(policy_id=policy_id,policy_code=row['policy_code'],display_name=row['display_name'],
        valuation_cut_id=row['valuation_cut_id'],strategy_id=row['strategy_id'],version_no=row['version_no'],status=row['status'],
        valid_from=row['valid_from'],valid_to=row['valid_to'],created_by=row['created_by_user_account_id'],
        created_at=row['created_at_utc'] if row['created_by_user_account_id'] else None,
        selection_mode=row['selection_mode'],
        rules=[PolicyRuleInput.model_validate({k:r[k] for k in PolicyRuleInput.model_fields}) for r in rules if not r['is_default']],
        default_rules=[PolicyRuleInput.model_validate({k:r[k] for k in PolicyRuleInput.model_fields}) for r in rules if r['is_default']])


def create_policy(c: Connection,tenant: UUID,actor: UUID,payload: PolicyCreate,key: str) -> PolicyDefinition:
    """Create/replay one version inside the caller's transaction and audit scope."""
    authority(c,tenant,actor,True)
    # The same action/scope guard applies outside HTTP and before replay.
    if payload.strategy_id:
        require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',payload.strategy_id)
    canonical=payload.model_dump(mode='json')
    for group in ('rules','default_rules'):
        for rule in canonical[group]:
            # Preserve retry fingerprints for pre-economic-requirement requests.
            if rule['price_requirement'] is None:
                rule.pop('price_requirement')
            if not rule['allow_split_conversion']:
                rule.pop('allow_split_conversion')
            if not rule['allow_inverse_fx']:
                rule.pop('allow_inverse_fx')
            if not rule['require_official_close']:
                rule.pop('require_official_close')
    # Retain replay compatibility with policy submissions made before mode support.
    if payload.selection_mode=='STRICT' and not payload.default_rules:
        canonical.pop('selection_mode'); canonical.pop('default_rules')
    digest=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Pre-consolidation retries keep their original immutable request identity.
    legacy=deepcopy(canonical)
    for group in ('rules','default_rules'):
        for rule in legacy.get(group,[]):
            if rule.pop('require_official_close',False):
                rule['series_type']='OFFICIAL_CLOSE'
    legacy_digest=hashlib.sha256(json.dumps(legacy,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def lock(scope):
        lock_id=int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8],'big',signed=True)
        c.execute(select(func.pg_advisory_xact_lock(lock_id)))
    lock(f'policy-key:{tenant}:{key}')
    old=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.submission_key==key)).mappings().one_or_none()
    if old:
        if old['submission_fingerprint'] not in (digest,legacy_digest):
            raise IdempotencyKeyConflict('Policy key reused')
        return policy_definition(c,tenant,old['valuation_policy_id'])
    if payload.strategy_id:
        from security_master_schema.market_data_resolver import assert_strategy_scope
        assert_strategy_scope(c,tenant,payload.strategy_id,payload.valid_from)
    checks=[(m.valuation_cut,m.valuation_cut.c.valuation_cut_id,payload.valuation_cut_id)]
    for rule in payload.rules + payload.default_rules:
        if rule.pricing_convention=='LEGACY' and (rule.pricing_cut_id or rule.fixing_code or rule.value_basis):
            raise ValueError('Legacy semantics cannot apply composite pricing-time or value-basis filters; choose a composite convention')
        checks.extend([(m.market_venue,m.market_venue.c.market_venue_id,rule.market_venue_id),
                       (m.valuation_cut,m.valuation_cut.c.valuation_cut_id,rule.pricing_cut_id),
                       (m.instrument_type,m.instrument_type.c.instrument_type_id,rule.instrument_type_id)])
        if rule.market_calendar_id:
            from market_data.calendar_store import visible_calendar
            reference=visible_calendar(c,tenant,rule.market_calendar_id)
            if not reference or (reference['tenant_id'] and rule.pricing_convention!='NAV_DATE'):
                raise ValueError('Exchange/fixing target calendars must be platform references; use NAV_DATE for a tenant fund calendar')
            if rule.pricing_convention=='NAV_DATE' and (reference['calendar_kind']!='VALUATION' or not reference['sealed']):
                raise ValueError('NAV_DATE requires a published tenant VALUATION calendar')
        if rule.subject_reference_node_id and not c.scalar(select(m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.reference_node_id==rule.subject_reference_node_id,
            catalogue_subject_clause(rule.subject_reference_node_id,tenant))):
            raise ValueError('Subject is not available to this tenant')
        if rule.market_data_series_id:
            series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==rule.market_data_series_id,
                m.market_data_series.c.status=='ACTIVE',catalogue_subject_clause(m.market_data_series.c.reference_node_id,tenant))).mappings().one_or_none()
            if not series or close_type(series['series_type'])!=rule.series_type or (rule.require_official_close and series['closing_method']!='EXCHANGE_OFFICIAL') or (rule.subject_reference_node_id and series['reference_node_id']!=rule.subject_reference_node_id):
                raise ValueError('Series is not available or inconsistent with the rule')
        if rule.dataset_id and not c.scalar(select(m.tenant_dataset_entitlement.c.dataset_id).where(
            m.tenant_dataset_entitlement.c.dataset_id==rule.dataset_id,m.tenant_dataset_entitlement.c.tenant_id==tenant,
            m.tenant_dataset_entitlement.c.status=='ACTIVE')):
            raise ValueError('Dataset is not available to this tenant')
    for table,id_col,value in checks:
        if value and not c.scalar(select(id_col).where(id_col==value,table.c.status=='ACTIVE') if 'status' in table.c else select(id_col).where(id_col==value)):
            raise ValueError('Inactive or unknown configuration reference')
    lock(f'policy-code:{tenant}:{payload.policy_code}')
    version_no=(c.scalar(select(func.max(m.valuation_policy.c.version_no)).where(m.valuation_policy.c.tenant_id==tenant,
        m.valuation_policy.c.policy_code==payload.policy_code)) or 0)+1
    policy_id=c.execute(m.valuation_policy.insert().values(tenant_id=tenant,policy_code=payload.policy_code,
        display_name=payload.display_name,valuation_cut_id=payload.valuation_cut_id,strategy_id=payload.strategy_id,
        selection_mode=payload.selection_mode,
        version_no=version_no,status='DRAFT',valid_from=payload.valid_from,valid_to=payload.valid_to,
        created_by_user_account_id=actor,submission_key=key,submission_fingerprint=digest).returning(m.valuation_policy.c.valuation_policy_id)).scalar_one()
    for is_default, rules in [(False,payload.rules),(True,payload.default_rules)]:
        for rule in rules:
            c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=policy_id,status='ACTIVE',is_default=is_default,**rule.model_dump()))
    c.execute(m.valuation_policy.update().where(m.valuation_policy.c.valuation_policy_id==policy_id).values(status='ACTIVE'))
    return policy_definition(c,tenant,policy_id)

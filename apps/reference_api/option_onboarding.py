"""Governed fixed-strike vanilla options; existing listing workflow stays separate."""
from datetime import datetime, timezone, date
import json
from sqlalchemy import select, or_
from security_master_schema import models as m
from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action,TenantActionForbidden
from .contracts import OptionProposalRequest
from .repository import RepositoryNotFound, InvalidWorkflowState, _visible_reference_node, _active_index_catalogue_reference, get_reference_data_proposal


def validate_references(connection,tenant_id,request):
    _visible_reference_node(connection,tenant_id,request.underlying_id)
    kind=underlying_kind(connection,tenant_id,request.underlying_id)
    if kind=='INDEX' and request.settlement_method!='CASH': raise InvalidWorkflowState('Index options must cash settle in this slice.')
    for currency in {request.strike_currency_id,request.premium_currency_id}:
        _active_index_catalogue_reference(connection,m.currency,m.currency.c.currency_id,currency,'Option currency')
    return kind


def underlying_kind(connection,tenant_id,underlying_id):
    _visible_reference_node(connection,tenant_id,underlying_id)
    today=date.today()
    definition=m.instrument_definition_version
    kind=connection.scalar(select(m.instrument_type.c.type_code).join(m.instrument,m.instrument.c.instrument_type_id==m.instrument_type.c.instrument_type_id).join(definition,definition.c.instrument_node_id==m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==underlying_id,m.instrument.c.is_current,m.instrument_type.c.status=='ACTIVE',definition.c.instrument_type_id==m.instrument.c.instrument_type_id,definition.c.is_current,definition.c.status=='APPROVED',definition.c.effective_from<=today,or_(definition.c.effective_to.is_(None),definition.c.effective_to>=today)))
    if kind in {'EQUITY','ETF','ETC','ETN','ETV','ETI'}: return kind
    if connection.scalar(select(m.index_terms.c.index_node_id).where(m.index_terms.c.index_node_id==underlying_id,m.index_terms.c.status=='ACTIVE')): return 'INDEX'
    raise InvalidWorkflowState('An active governed equity, ETP or index underlying is required.')


def submit_option_proposal(connection,tenant_id,actor_id,request):
    from .reference_authority import require_reference_action
    require_reference_action(connection,tenant_id,actor_id)
    from .proposal_retries import find_proposal_replay
    replay=find_proposal_replay(connection,tenant_id,request,require_source=False)
    if replay is not None:
        return get_reference_data_proposal(connection,tenant_id,replay)
    validate_references(connection,tenant_id,request)
    payload=request.model_dump(mode='json',by_alias=True)
    payload['proposedByUserAccountId']=str(actor_id)
    proposal_id=connection.scalar(m.reference_data_proposal.insert().values(tenant_id=tenant_id,proposal_type='CREATE_OPTION',proposed_payload=json.dumps(payload,sort_keys=True),submission_mode='MANUAL',match_status='NEW',payload_schema_version='option.v1',status='PENDING',idempotency_key=request.idempotency_key).returning(m.reference_data_proposal.c.reference_data_proposal_id))
    return get_reference_data_proposal(connection,tenant_id,proposal_id)


def decide_option_proposal(connection,tenant_id,actor_id,proposal_id,decision,reason):
    from .reference_authority import require_reference_action
    require_reference_action(connection,tenant_id,actor_id,'REFERENCE_APPROVE')
    row=connection.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.tenant_id==tenant_id,m.reference_data_proposal.c.reference_data_proposal_id==proposal_id).with_for_update()).mappings().first()
    if row is None: raise RepositoryNotFound('Option proposal was not found.')
    if row.proposal_type!='CREATE_OPTION' or row.status!='PENDING': raise InvalidWorkflowState('Only pending option proposals can be decided.')
    payload=json.loads(row.proposed_payload)
    payload.pop('proposedByUserAccountId',None)
    request=OptionProposalRequest.model_validate(payload)
    node=None
    if decision=='APPROVED':
        kind=validate_references(connection,tenant_id,request)
        node_type=connection.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='INSTRUMENT',m.reference_node_type.c.status=='ACTIVE'))
        instrument_type=connection.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code=='OPTION',m.instrument_type.c.status=='ACTIVE'))
        if not node_type or not instrument_type: raise InvalidWorkflowState('Active option reference types are required.')
        node=connection.scalar(m.financial_reference_node.insert().values(reference_node_type_id=node_type,canonical_name=request.canonical_name,status='ACTIVE',is_tradable=True).returning(m.financial_reference_node.c.reference_node_id))
        fields=dict(instrument_type_id=instrument_type,asset_class='DERIVATIVE',base_currency_id=request.premium_currency_id,effective_from=request.effective_from,is_current=True,sequence_no=1)
        connection.execute(m.instrument.insert().values(instrument_node_id=node,**fields))
        connection.execute(m.instrument_definition_version.insert().values(instrument_node_id=node,**fields,status='APPROVED',approved_by_user_account_id=actor_id,approved_at_utc=datetime.now(timezone.utc)))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant_id,status='ACTIVE'))
        connection.execute(m.instrument_dates.insert().values(instrument_node_id=node,effective_date=request.effective_from,expiry_date=request.expiry_date,last_trading_date=request.last_trading_at_utc.astimezone(timezone.utc).date()))
        connection.execute(m.instrument_contract_unit_terms.insert().values(instrument_node_id=node,unit_multiplier=request.deliverable_units,unit_of_measure='INDEX_POINT' if kind=='INDEX' else 'SHARE',valid_from=request.effective_from))
        connection.execute(m.option_terms.insert().values(instrument_node_id=node,effective_from=request.effective_from,underlying_reference_node_id=request.underlying_id,option_type=request.option_type,exercise_style=request.exercise_style,strike_value=request.strike,strike_mode='FIXED',strike_basis='ABSOLUTE',strike_currency_id=request.strike_currency_id,premium_currency_id=request.premium_currency_id,premium_multiplier=request.premium_multiplier,premium_style='UPFRONT',last_trading_at_utc=request.last_trading_at_utc,settlement_method=request.settlement_method,settlement_currency_id=request.premium_currency_id if request.settlement_method=='CASH' else None,status='ACTIVE',is_current=True))
    now=datetime.now(timezone.utc)
    connection.execute(m.reference_data_approval.insert().values(reference_data_proposal_id=proposal_id,decision=decision,decided_by_user_account_id=actor_id,decision_method='MANUAL',decision_evidence_json={'manualDecision':True,'reason':reason},decided_at_utc=now,reason=reason))
    connection.execute(m.reference_data_proposal.update().where(m.reference_data_proposal.c.reference_data_proposal_id==proposal_id).values(status=decision,reference_node_id=node))
    return get_reference_data_proposal(connection,tenant_id,proposal_id)

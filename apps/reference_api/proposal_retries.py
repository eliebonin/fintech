"""Source-scoped proposal replay: serialize retries and preserve request intent."""
import json
from sqlalchemy import select, func
from pydantic import ValidationError
from security_master_schema import models as m
from .booking_controls import booking_lock_key
from .booking_errors import IdempotencyKeyConflict, InvalidWorkflowState


def proposal_request_payload(payload):
    """Remove only known server metadata before strict request reconstruction."""
    return {key:value for key,value in payload.items() if key not in {'proposedByUserAccountId','enrichmentStatus'}}


def find_proposal_replay(connection, tenant_id, request, *, require_source=True):
    if not request.idempotency_key:
        return None
    source_id = getattr(request, 'source_system_id', None)
    if require_source and source_id is None:
        raise InvalidWorkflowState('idempotencyKey requires sourceSystemId')
    # The unique constraint spans proposal types, so the lock must too.
    scope = f'reference-proposal:{source_id}'
    connection.execute(select(func.pg_advisory_xact_lock(
        booking_lock_key(tenant_id, scope, request.idempotency_key))))
    row = connection.execute(select(m.reference_data_proposal).where(
        m.reference_data_proposal.c.tenant_id == tenant_id,
        m.reference_data_proposal.c.source_system_id == source_id,
        m.reference_data_proposal.c.idempotency_key == request.idempotency_key
    ).with_for_update()).mappings().first()
    if row is None:
        return None
    schemas = {
        'EquityProposalRequest': 'equity.v1',
        'EquityListingCreateProposalRequest': 'equity-listing.v1',
        'BondProposalRequest': 'bond.v1', 'CryptoAssetProposalRequest': 'crypto-asset.v1',
        'FxForwardProposalRequest': 'fx-forward.v1', 'EtpProposalRequest': 'etp.v1',
        'IndexFamilyProposalRequest': 'index-family.v1', 'IndexProposalRequest': 'index.v1',
        'AutocallDraftRequest': 'structured-product.v1',
        'OptionProposalRequest': 'option.v1',
        'SwapProposalRequest': 'product-booking.v1',
        'FutureProposalRequest': 'product-booking.v1',
        'FutureFamilyProposalRequest': 'product-booking.v1',
        'ConventionProposalRequest': 'product-booking.v1',
    }
    conflict = IdempotencyKeyConflict('Idempotency key was already used with a different proposal request')
    if row['payload_schema_version'] != schemas.get(type(request).__name__):
        raise conflict
    expected_kind = {'SwapProposalRequest':'CREATE_SWAP', 'FutureProposalRequest':'CREATE_FUTURE',
        'FutureFamilyProposalRequest':'CREATE_FUTURE_FAMILY', 'ConventionProposalRequest':'CONFIGURE_BOOKING_CONVENTION'}.get(type(request).__name__)
    if expected_kind and row['proposal_type'] != expected_kind:
        raise conflict
    payload = json.loads(row['proposed_payload'])
    for field in ('proposedByUserAccountId', 'enrichmentStatus'):
        payload.pop(field, None)
    try:
        original = type(request).model_validate(payload)
    except ValidationError as exc:
        raise conflict from exc
    # Typed normalization handles defaults and equivalent decimal spellings.
    if original.model_dump(by_alias=True, exclude_none=True) != request.model_dump(by_alias=True, exclude_none=True):
        raise conflict
    return row['reference_data_proposal_id']

"""Governed booking of funded structured securities and cash-settled index futures."""
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from uuid import UUID, uuid4
from pydantic import TypeAdapter
from sqlalchemy import select, exists, and_, or_, func
from security_master_schema import models as m
from security_master_schema.product_booking import execution_amount, validate_increment, bond_amounts, swap_reference_value
from security_master_schema.fx_forward_booking import decimal_text
from .product_booking_contracts import (
    BookingConvention, ConventionProposalRequest, FutureProposalRequest, FutureFamilyProposalRequest, FutureFamilyView, FutureFamilySpecification,
    ProductBookingContextView, ProductTradeEconomicsView,
)
from .swap_creation_contracts import SwapProposalRequest
from .booking_controls import authorize_booking, lock_booking_strategy, find_booking_replay, record_booking_replay

CONVENTION = TypeAdapter(BookingConvention)


class ProductBookingError(ValueError):
    def __init__(self, message, field='instrumentId', code='product.invalid_booking'):
        super().__init__(message)
        self.field, self.code = field, code


class ProductValuationUnsupported(ValueError):
    pass


def visible_clause(reference_id, tenant):
    scope = m.reference_node_scope.alias()
    return ~exists(select(1).select_from(scope).where(
        scope.c.reference_node_id == reference_id,
        ~and_(scope.c.status == 'ACTIVE', or_(scope.c.scope_type == 'SHARED_CANONICAL',
             and_(scope.c.scope_type == 'TENANT_PRIVATE', scope.c.owner_tenant_id == tenant)))))


def require_visible(connection, tenant, node_id):
    from .repository import RepositoryNotFound
    node = connection.execute(select(m.financial_reference_node).where(
        m.financial_reference_node.c.reference_node_id == node_id,
        m.financial_reference_node.c.status == 'ACTIVE', visible_clause(node_id, tenant))).mappings().first()
    if node is None: raise RepositoryNotFound('Active visible reference was not found.')
    return node


def require_owned(connection, tenant, node_id):
    require_visible(connection, tenant, node_id)
    if not connection.scalar(select(m.reference_node_scope.c.reference_node_id).where(
        m.reference_node_scope.c.reference_node_id == node_id,
        m.reference_node_scope.c.scope_type == 'TENANT_PRIVATE',
        m.reference_node_scope.c.owner_tenant_id == tenant, m.reference_node_scope.c.status == 'ACTIVE')):
        raise ProductBookingError('Only tenant-owned instruments can be configured in this alpha.')


def instrument_row(connection, tenant, node_id):
    from .repository import RepositoryNotFound
    node = require_visible(connection, tenant, node_id)
    row = connection.execute(select(m.instrument, m.instrument_type.c.type_code,
        m.instrument_type.c.status.label('type_status')).join(m.instrument_type,
        m.instrument_type.c.instrument_type_id == m.instrument.c.instrument_type_id).where(
        m.instrument.c.instrument_node_id == node_id)).mappings().first()
    if row is None or row.type_code not in {'STRUCTURED_PRODUCT', 'FUTURE', 'BOND', 'SWAP'}:
        raise RepositoryNotFound('A structured security or futures instrument is required.')
    return node, row


def validate_convention_references(connection, tenant, instrument_id, convention):
    require_owned(connection, tenant, instrument_id)
    _, instrument = instrument_row(connection, tenant, instrument_id)
    if instrument.type_code != convention.kind or convention.price_currency_id != instrument.base_currency_id:
        raise ProductBookingError('Convention kind/currency must agree with the canonical instrument.')
    if not connection.scalar(select(m.currency.c.currency_id).where(
        m.currency.c.currency_id == convention.price_currency_id, m.currency.c.status == 'ACTIVE')):
        raise ProductBookingError('An active price currency is required.')
    if convention.effective_from < instrument.effective_from:
        raise ProductBookingError('Convention cannot precede the instrument effective date.')
    if convention.kind == 'FUTURE':
        future = connection.execute(select(m.future_terms).where(m.future_terms.c.instrument_node_id == instrument_id)).mappings().first()
        family = connection.execute(select(m.future_family).where(m.future_family.c.future_family_id == future.future_family_id)).mappings().first() if future else None
        specification = FutureFamilySpecification.model_validate_json(family.specification_payload) if family and family.specification_payload else None
        if specification and specification.underlying_kind == 'CRYPTOASSET':
            raise ProductBookingError('Crypto futures are creation-only; booking-convention amendment is deferred.')
        if not future or future.settlement_method != convention.settlement_method or future.delivery_start_date != convention.delivery_start_date or future.delivery_end_date != convention.delivery_end_date:
            raise ProductBookingError('Convention changes cannot alter canonical futures delivery terms.')
        if specification:
            for field in ('price_basis', 'settlement_method', 'contract_size', 'contract_size_currency_id', 'monetary_multiplier', 'quote_factor', 'tick_size', 'allow_negative_price'):
                if getattr(convention, field) != getattr(specification, field):
                    raise ProductBookingError('Conventions must agree with the approved family specification.')
        dates = connection.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == instrument_id)).mappings().one_or_none()
        previous = connection.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id == instrument_id).order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().first()
        if not dates or dates.final_settlement_date != convention.final_settlement_date or dates.last_trading_date != convention.last_trading_at_utc.astimezone(timezone.utc).date():
            raise ProductBookingError('Convention changes cannot change the canonical futures expiry or final settlement.')
        if previous and CONVENTION.validate_json(previous.convention_payload).last_trading_at_utc != convention.last_trading_at_utc:
            raise ProductBookingError('Convention changes cannot change the approved trading cutoff instant.')
    return instrument


def append_convention(connection, instrument_id, convention, actor):
    connection.execute(select(m.instrument).where(m.instrument.c.instrument_node_id == instrument_id).with_for_update()).all()
    version = (connection.scalar(select(func.max(m.instrument_booking_convention.c.version_no)).where(
        m.instrument_booking_convention.c.instrument_node_id == instrument_id)) or 0) + 1
    connection.execute(m.instrument_booking_convention.insert().values(
        instrument_node_id=instrument_id, version_no=version, effective_from=convention.effective_from,
        kind=convention.kind, convention_payload=convention.model_dump_json(by_alias=True),
        approved_by_user_account_id=actor))


def submit_proposal(connection, tenant, actor, request):
    from .repository import get_reference_data_proposal
    if isinstance(request, SwapProposalRequest):
        from .swap_creation import validate_swap_references
        validate_swap_references(connection, tenant, request.terms)
        kind = 'CREATE_SWAP'
    elif isinstance(request, ConventionProposalRequest):
        validate_convention_references(connection, tenant, request.instrument_id, request.convention)
        kind = 'CONFIGURE_BOOKING_CONVENTION'
    elif isinstance(request, FutureFamilyProposalRequest):
        validate_family_references(connection, tenant, request.underlying_id, request.contract_currency_id, request.specification)
        kind = 'CREATE_FUTURE_FAMILY'
    else:
        validate_future_underlying(connection, tenant, request)
        kind = 'CREATE_FUTURE'
    payload = request.model_dump(mode='json', by_alias=True) | {'proposedByUserAccountId': str(actor)}
    proposal_id = connection.scalar(m.reference_data_proposal.insert().values(
        tenant_id=tenant, proposal_type=kind, proposed_payload=json.dumps(payload, sort_keys=True),
        submission_mode='MANUAL', match_status='NEW', payload_schema_version='product-booking.v1',
        status='PENDING').returning(m.reference_data_proposal.c.reference_data_proposal_id))
    return get_reference_data_proposal(connection, tenant, proposal_id)


def validate_family_references(connection, tenant, underlying_id, currency_id, specification=None):
    require_visible(connection, tenant, underlying_id)
    if specification and specification.underlying_kind == 'CRYPTOASSET':
        asset = connection.execute(select(m.currency).where(m.currency.c.reference_node_id == underlying_id,
            m.currency.c.status == 'ACTIVE', m.currency.c.currency_kind.in_(['CRYPTOASSET', 'STABLECOIN']))).mappings().first()
        if not asset or asset.currency_id != specification.contract_size_currency_id:
            raise ProductBookingError('Contract-size currency must be the governed underlying cryptoasset.')
        if not connection.scalar(select(m.crypto_asset_terms.c.instrument_node_id).where(
            m.crypto_asset_terms.c.instrument_node_id == underlying_id, m.crypto_asset_terms.c.is_current,
            m.crypto_asset_terms.c.status == 'ACTIVE')):
            raise ProductBookingError('An active governed cryptoasset is required.')
    elif not connection.scalar(select(m.index_terms.c.index_node_id).where(
        m.index_terms.c.index_node_id == underlying_id, m.index_terms.c.status == 'ACTIVE')):
        raise ProductBookingError('Select an active index or an explicitly configured cryptoasset family.')
    currency = connection.execute(select(m.currency).where(m.currency.c.currency_id == currency_id, m.currency.c.status == 'ACTIVE')).mappings().first()
    if not currency: raise ProductBookingError('An active contract currency is required.')
    if currency.reference_node_id: require_visible(connection, tenant, currency.reference_node_id)


def validate_future_underlying(connection, tenant, request):
    specification = None
    if request.family_id:
        family = connection.execute(select(m.future_family).where(m.future_family.c.future_family_id == request.family_id)).mappings().first()
        if not family: raise ProductBookingError('Approved family was not found.')
        specification = FutureFamilySpecification.model_validate_json(family.specification_payload) if family.specification_payload else None
        require_owned(connection, tenant, family.family_node_id)
        node = require_visible(connection, tenant, family.family_node_id)
        if family.status != 'ACTIVE' or family.underlying_reference_node_id != request.underlying_id or family.contract_currency_id != request.convention.price_currency_id or node.internal_code != f'FUTURE_FAMILY_{tenant.hex}_{request.family_code}':
            raise ProductBookingError('Selected family identity, underlying and currency must agree.')
    validate_family_references(connection, tenant, request.underlying_id, request.convention.price_currency_id, specification)
    if specification:
        if request.contract_month.month not in specification.delivery_months:
            raise ProductBookingError('Contract month is outside the approved family delivery cycle.')
        for field in ('price_basis', 'settlement_method', 'contract_size', 'contract_size_currency_id', 'monetary_multiplier', 'quote_factor', 'tick_size', 'allow_negative_price'):
            if getattr(request.convention, field) != getattr(specification, field):
                raise ProductBookingError('Expiry economics must agree with the approved family specification.')
    elif request.convention.price_basis != 'INDEX_POINTS' or request.convention.settlement_method != 'CASH':
        raise ProductBookingError('Legacy families only support cash-settled index conventions.')
    if request.contract_month.day != 1:
        raise ProductBookingError('Contract month must be its first calendar day.')
    if request.contract_month.strftime('%Y-%m') != request.convention.final_settlement_date.strftime('%Y-%m'):
        raise ProductBookingError('This alpha requires final settlement in the stated contract month.')


def materialize_future(connection, tenant, actor, request):
    from .repository import InvalidWorkflowState
    validate_future_underlying(connection, tenant, request)
    def type_id(table, code):
        key = table.c.reference_node_type_id if table is m.reference_node_type else table.c.instrument_type_id
        result = connection.scalar(select(key).where(table.c.type_code == code, table.c.status == 'ACTIVE'))
        if not result: raise InvalidWorkflowState(f'Active {code} catalogue is required.')
        return result
    # Family identity is scoped by tenant; the same exchange root may exist for another tenant.
    family_code = f'FUTURE_FAMILY_{tenant.hex}_{request.family_code}'
    connection.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(family_code.encode()).digest()[:8], 'big', signed=True))))
    family = connection.execute(select(m.future_family).join(m.financial_reference_node,
        m.financial_reference_node.c.reference_node_id == m.future_family.c.family_node_id).where(
        m.financial_reference_node.c.internal_code == family_code)).mappings().first()
    if family:
        require_owned(connection, tenant, family.family_node_id)
        if family.status != 'ACTIVE' or family.underlying_reference_node_id != request.underlying_id or family.contract_currency_id != request.convention.price_currency_id:
            raise ProductBookingError('Existing family underlying/currency differs. Use the correct family code.')
        family_id = family.future_family_id
    else:
        family_node = connection.scalar(m.financial_reference_node.insert().values(
            reference_node_type_id=type_id(m.reference_node_type, 'FUTURE_FAMILY'),
            canonical_name=request.family_code, internal_code=family_code, is_tradable=False,
            status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=family_node,
            scope_type='TENANT_PRIVATE', owner_tenant_id=tenant, status='ACTIVE'))
        family_id = connection.scalar(m.future_family.insert().values(family_node_id=family_node,
            underlying_reference_node_id=request.underlying_id, contract_currency_id=request.convention.price_currency_id,
            status='ACTIVE').returning(m.future_family.c.future_family_id))
    if connection.scalar(select(m.future_terms.c.instrument_node_id).where(
        m.future_terms.c.future_family_id == family_id, m.future_terms.c.contract_month == request.contract_month)):
        raise ProductBookingError('This family already has that expiry. Use its existing instrument.')
    node_id = connection.scalar(m.financial_reference_node.insert().values(
        reference_node_type_id=type_id(m.reference_node_type, 'INSTRUMENT'), canonical_name=request.canonical_name.strip(),
        is_tradable=True, status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
    fields = dict(instrument_type_id=type_id(m.instrument_type, 'FUTURE'), asset_class='DERIVATIVE',
        base_currency_id=request.convention.price_currency_id, effective_from=request.convention.effective_from,
        is_current=True, sequence_no=1)
    connection.execute(m.instrument.insert().values(instrument_node_id=node_id, **fields))
    connection.execute(m.instrument_definition_version.insert().values(instrument_node_id=node_id, **fields,
        status='APPROVED', approved_by_user_account_id=actor, approved_at_utc=datetime.now(timezone.utc)))
    connection.execute(m.reference_node_scope.insert().values(reference_node_id=node_id,
        scope_type='TENANT_PRIVATE', owner_tenant_id=tenant, status='ACTIVE'))
    connection.execute(m.future_terms.insert().values(instrument_node_id=node_id, future_family_id=family_id,
        contract_month=request.contract_month, last_trade_date=request.convention.last_trading_at_utc.astimezone(timezone.utc).date(),
        settlement_method=request.convention.settlement_method, delivery_start_date=request.convention.delivery_start_date,
        delivery_end_date=request.convention.delivery_end_date))
    connection.execute(m.instrument_dates.insert().values(instrument_node_id=node_id,
        effective_date=request.convention.effective_from, expiry_date=request.convention.last_trading_at_utc.astimezone(timezone.utc).date(),
        last_trading_date=request.convention.last_trading_at_utc.astimezone(timezone.utc).date(),
        final_settlement_date=request.convention.final_settlement_date))
    append_convention(connection, node_id, request.convention, actor)
    return node_id


def decide_proposal(connection, tenant, actor, proposal_id, decision, reason):
    from .repository import get_reference_data_proposal, RepositoryNotFound, InvalidWorkflowState
    from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action
    workspace = resolve_tenant_workspace(connection, tenant, actor, date.today())
    if workspace.membership_role != 'TENANT_ADMIN': raise InvalidWorkflowState('Tenant administrator approval is required.')
    require_tenant_action(workspace, 'TRADE_WRITE')
    row = connection.execute(select(m.reference_data_proposal).where(
        m.reference_data_proposal.c.reference_data_proposal_id == proposal_id,
        m.reference_data_proposal.c.tenant_id == tenant).with_for_update()).mappings().first()
    if not row: raise RepositoryNotFound('Proposal was not found.')
    if row.status != 'PENDING' or row.proposal_type not in {'CREATE_SWAP', 'CREATE_FUTURE', 'CREATE_FUTURE_FAMILY', 'CONFIGURE_BOOKING_CONVENTION'}:
        raise InvalidWorkflowState('Only pending product booking proposals can be decided.')
    payload = json.loads(row.proposed_payload)
    payload.pop('proposedByUserAccountId', None)
    request = {'CREATE_SWAP': SwapProposalRequest, 'CREATE_FUTURE': FutureProposalRequest, 'CREATE_FUTURE_FAMILY': FutureFamilyProposalRequest, 'CONFIGURE_BOOKING_CONVENTION': ConventionProposalRequest}[row.proposal_type].model_validate(payload)
    node_id = None
    if decision == 'APPROVED':
        if isinstance(request, SwapProposalRequest):
            from .swap_creation import materialize_swap
            node_id = materialize_swap(connection, tenant, actor, request)
        elif isinstance(request, FutureFamilyProposalRequest): node_id = materialize_family(connection, tenant, request)
        elif isinstance(request, FutureProposalRequest): node_id = materialize_future(connection, tenant, actor, request)
        else:
            connection.execute(select(m.instrument).where(m.instrument.c.instrument_node_id == request.instrument_id).with_for_update()).all()
            validate_convention_references(connection, tenant, request.instrument_id, request.convention)
            append_convention(connection, request.instrument_id, request.convention, actor)
            node_id = request.instrument_id
    connection.execute(m.reference_data_approval.insert().values(reference_data_proposal_id=proposal_id,
        decision=decision, decided_by_user_account_id=actor, decision_method='MANUAL',
        decision_evidence_json={'manualDecision': True, 'reason': reason}, reason=reason))
    connection.execute(m.reference_data_proposal.update().where(
        m.reference_data_proposal.c.reference_data_proposal_id == proposal_id).values(status=decision, reference_node_id=node_id))
    return get_reference_data_proposal(connection, tenant, proposal_id)


def lock_booking_currency(connection, instrument_id):
    """Acquire the common currency phase before contract/source identity rows."""
    currency_id = connection.scalar(select(m.instrument.c.base_currency_id).where(
        m.instrument.c.instrument_node_id == instrument_id))
    if currency_id is not None:
        connection.execute(select(m.currency).where(m.currency.c.currency_id == currency_id).with_for_update()).all()
    return currency_id


def load_context(connection, tenant, instrument_id, listing_id=None, as_of=None, lock=False):
    as_of = as_of or date.today()
    locked_currency_id = lock_booking_currency(connection, instrument_id) if lock else None
    if lock:
        # Lock the canonical instrument before reading conventions and listing projections.
        for table, key, value in [(m.financial_reference_node, 'reference_node_id', instrument_id),
             (m.reference_node_scope, 'reference_node_id', instrument_id), (m.instrument, 'instrument_node_id', instrument_id),
             (m.instrument_definition_version, 'instrument_node_id', instrument_id),
             (m.instrument_booking_convention, 'instrument_node_id', instrument_id),
             (m.structured_product_terms, 'instrument_node_id', instrument_id),
             (m.bond_terms, 'instrument_node_id', instrument_id),
             (m.future_terms, 'instrument_node_id', instrument_id), (m.instrument_dates, 'instrument_node_id', instrument_id)]:
            connection.execute(select(table).where(table.c[key] == value).with_for_update()).all()
        if listing_id:
            for table, key in [(m.financial_reference_node, 'reference_node_id'), (m.reference_node_scope, 'reference_node_id'),
                (m.listing, 'listing_node_id'), (m.listing_definition_version, 'listing_node_id')]:
                connection.execute(select(table).where(table.c[key] == listing_id).with_for_update()).all()
    node, instrument = instrument_row(connection, tenant, instrument_id)
    listing_node = require_visible(connection, tenant, listing_id) if listing_id else None
    values = dict(instrumentId=instrument_id, name=node.canonical_name, kind=instrument.type_code,
        listingId=listing_id, listingName=listing_node.canonical_name if listing_node else None,
        executionRoute='LISTED' if listing_id else 'OTC')
    try:
        if lock and instrument.base_currency_id != locked_currency_id:
            raise ValueError('Instrument currency changed while acquiring booking locks. Reselect the instrument.')
        if not node.is_tradable or not instrument.is_current or instrument.type_status != 'ACTIVE':
            raise ValueError('An active tradable instrument is required.')
        definitions = connection.execute(select(m.instrument_definition_version).where(
            m.instrument_definition_version.c.instrument_node_id == instrument_id,
            m.instrument_definition_version.c.is_current, m.instrument_definition_version.c.status == 'APPROVED')).mappings().all()
        if len(definitions) != 1: raise ValueError('Exactly one current approved instrument definition is required.')
        definition = definitions[0]
        for key in ('base_currency_id', 'instrument_type_id', 'issuer_organisation_id', 'effective_from', 'effective_to'):
            if definition[key] != instrument[key]: raise ValueError('Instrument differs from its approved definition.')
        if as_of < definition.effective_from or (definition.effective_to and as_of > definition.effective_to):
            raise ValueError('Execution date is outside the approved instrument definition.')
        stored = connection.execute(select(m.instrument_booking_convention).where(
            m.instrument_booking_convention.c.instrument_node_id == instrument_id,
            m.instrument_booking_convention.c.effective_from <= as_of).order_by(
            m.instrument_booking_convention.c.effective_from.desc(), m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().first()
        if not stored: raise ValueError('Approved booking conventions are required. Configure them from instrument detail.')
        convention = CONVENTION.validate_json(stored.convention_payload)
        values['convention'] = convention
        if convention.kind != instrument.type_code or convention.price_currency_id != definition.base_currency_id:
            raise ValueError('Approved convention kind/currency does not agree with the instrument.')
        currency_stmt = select(m.currency).where(m.currency.c.currency_id == convention.price_currency_id)
        currency = connection.execute(currency_stmt.with_for_update() if lock else currency_stmt).mappings().one()
        if currency.status != 'ACTIVE': raise ValueError('Price currency must be active.')
        values['currency'] = currency.currency_code
        facts = dict(conventionId=str(stored.instrument_booking_convention_id), definitionId=str(definition.instrument_definition_version_id))
        if listing_id:
            listing = connection.execute(select(m.listing).where(m.listing.c.listing_node_id == listing_id)).mappings().first()
            versions = connection.execute(select(m.listing_definition_version).where(
                m.listing_definition_version.c.listing_node_id == listing_id,
                m.listing_definition_version.c.status == 'APPROVED', m.listing_definition_version.c.is_current)).mappings().all()
            if not listing or listing.instrument_node_id != instrument_id or listing.status != 'ACTIVE' or not listing_node.is_tradable or len(versions) != 1:
                raise ValueError('An active approved listing of this instrument is required.')
            version = versions[0]
            for key in ('market_venue_id', 'trading_currency_id', 'quote_factor', 'unit_multiplier', 'effective_from', 'effective_to'):
                if version[key] != listing[key]: raise ValueError('Listing differs from its approved definition.')
            if not version.effective_from <= as_of or (version.effective_to and as_of > version.effective_to):
                raise ValueError('Execution date is outside the listing definition.')
            if listing.trading_currency_id != convention.price_currency_id or listing.quote_factor != convention.quote_factor:
                raise ValueError('Listing quotation differs from the approved booking convention.')
            values['listingUnitMultiplier'] = listing.unit_multiplier
            venue_stmt = select(m.market_venue).where(m.market_venue.c.market_venue_id == listing.market_venue_id)
            venue = connection.execute(venue_stmt.with_for_update() if lock else venue_stmt).mappings().one()
            if venue.status != 'ACTIVE': raise ValueError('Execution venue must be active.')
            facts.update(listingDefinitionId=str(version.listing_definition_version_id), venueId=str(venue.market_venue_id))
        if convention.kind == 'STRUCTURED_PRODUCT':
            terms = connection.execute(select(m.structured_product_terms).where(
                m.structured_product_terms.c.instrument_node_id == instrument_id,
                m.structured_product_terms.c.is_current)).mappings().all()
            if len(terms) != 1 or terms[0].status not in {'ACTIVE', 'VALIDATED'} or terms[0].effective_from > as_of or (terms[0].effective_to and terms[0].effective_to < as_of):
                raise ValueError('An effective approved structured-product terms graph is required.')
            if terms[0].issue_currency_id != convention.price_currency_id: raise ValueError('Cross-currency purchase settlement is deferred.')
            if not instrument.issuer_organisation_id: raise ValueError('An explicit issuer is required for funded securities.')
            issuer_stmt = select(m.organisation.c.status).where(m.organisation.c.organisation_id == instrument.issuer_organisation_id)
            if connection.scalar(issuer_stmt.with_for_update() if lock else issuer_stmt) != 'ACTIVE': raise ValueError('Issuer must be active.')
            dates = connection.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == instrument_id)).mappings().one_or_none()
            if not dates or not dates.maturity_date or as_of >= dates.maturity_date: raise ValueError('A future maturity date is required; matured securities cannot be booked in this alpha.')
            values['maturityDate'] = dates.maturity_date
            if not listing_id and not convention.otc_allowed: raise ValueError('OTC execution has not been approved for this instrument.')
            facts['structuredTermsId'] = str(terms[0].structured_product_terms_id)
        elif convention.kind == 'BOND':
            statement = select(m.bond_terms).where(m.bond_terms.c.instrument_node_id == instrument_id, m.bond_terms.c.is_current)
            terms = connection.execute(statement.with_for_update() if lock else statement).mappings().all()
            if len(terms) != 1 or terms[0].effective_from > as_of or (terms[0].effective_to and terms[0].effective_to < as_of):
                raise ValueError('Exactly one effective current bond terms record is required.')
            bond = terms[0]
            if bond.coupon_type not in {'FIXED', 'ZERO'} or bond.quotation_basis != 'PCT_OF_PAR' or bond.floating_reference_index or bond.floating_spread:
                raise ValueError('Only plain fixed/zero-coupon percentage-quoted bonds are supported.')
            if not bond.par_amount or bond.par_amount <= 0 or bond.redemption_amount_per_par != 100:
                raise ValueError('Sourced positive par and unadjusted redemption at par are required.')
            if bond.coupon_type == 'FIXED' and (bond.coupon_rate is None or bond.coupon_rate < 0 or not bond.coupon_frequency_per_year or not bond.day_count_convention):
                raise ValueError('Fixed coupon rate, frequency and day-count terms are required.')
            if bond.issue_currency_id != convention.price_currency_id:
                raise ValueError('Cross-currency bond settlement is deferred.')
            dates = connection.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == instrument_id)).mappings().one_or_none()
            if not dates or not dates.maturity_date or as_of >= dates.maturity_date:
                raise ValueError('A future maturity date is required.')
            if not listing_id and not convention.otc_allowed:
                raise ValueError('OTC execution has not been approved.')
            values.update(maturityDate=dates.maturity_date, couponType=bond.coupon_type, couponRate=bond.coupon_rate,
                couponFrequency=bond.coupon_frequency_per_year, dayCountConvention=bond.day_count_convention)
            facts['bondTerms'] = dict(bond)
        elif convention.kind == 'SWAP':
            if listing_id or not convention.otc_allowed:
                raise ValueError('This swap slice requires an approved OTC convention, without a listing.')
            from .swap_booking import load_swap_context
            details, maturity = load_swap_context(connection, tenant, instrument_id, as_of, lock=lock)
            values.update(swapDetails=details, maturityDate=maturity)
        else:
            future = connection.execute(select(m.future_terms).where(m.future_terms.c.instrument_node_id == instrument_id)).mappings().one_or_none()
            if future:
                values['contractMonth'] = future.contract_month
                display_family = connection.execute(select(m.future_family).where(m.future_family.c.future_family_id == future.future_family_id)).mappings().one()
                require_visible(connection, tenant, display_family.family_node_id)
                underlying = require_visible(connection, tenant, display_family.underlying_reference_node_id)
                values.update(underlyingId=underlying.reference_node_id, underlyingName=underlying.canonical_name)
            if not future or future.settlement_method != 'CASH' or convention.price_basis != 'INDEX_POINTS':
                raise ValueError('This futures contract is creation-only. Physical/crypto trade booking is deferred.')
            family_stmt = select(m.future_family).where(m.future_family.c.future_family_id == future.future_family_id)
            family = connection.execute(family_stmt.with_for_update() if lock else family_stmt).mappings().one()
            if lock:
                for ref in (family.family_node_id, family.underlying_reference_node_id):
                    for table in (m.financial_reference_node, m.reference_node_scope):
                        connection.execute(select(table).where(table.c.reference_node_id == ref).with_for_update()).all()
                connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id == family.underlying_reference_node_id).with_for_update()).all()
            require_visible(connection, tenant, family.family_node_id)
            require_visible(connection, tenant, family.underlying_reference_node_id)
            if family.status != 'ACTIVE' or family.contract_currency_id != convention.price_currency_id:
                raise ValueError('Active matching futures family is required.')
            if not connection.scalar(select(m.index_terms.c.index_node_id).where(m.index_terms.c.index_node_id == family.underlying_reference_node_id, m.index_terms.c.status == 'ACTIVE')):
                raise ValueError('Only governed index futures are supported.')
            if as_of > convention.last_trading_at_utc.astimezone(timezone.utc).date(): raise ValueError('Contract is past its trading cutoff.')
            dates = connection.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == instrument_id)).mappings().one_or_none()
            if not dates or dates.final_settlement_date != convention.final_settlement_date or dates.last_trading_date != convention.last_trading_at_utc.astimezone(timezone.utc).date() or future.last_trade_date != dates.last_trading_date:
                raise ValueError('Canonical futures dates differ from approved booking conventions.')
            values['contractMonth'] = future.contract_month
            if not listing_id: raise ValueError('Futures booking requires an exact expiry listing.')
            facts.update(familyId=str(family.future_family_id), underlyingId=str(family.underlying_reference_node_id))
        snapshot = ProductBookingContextView(**values)
        facts.update(snapshot.model_dump(mode='json', by_alias=True))
        values.update(bookingEligible=True, termsFingerprint=sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest())
    except ValueError as error:
        values['ineligibilityMessage'] = str(error)
    return ProductBookingContextView(**values)


def search(connection, tenant, kind, route, query, limit, offset, as_of):
    node = m.financial_reference_node
    statement = select(m.instrument.c.instrument_node_id, node.c.canonical_name).join(node,
        node.c.reference_node_id == m.instrument.c.instrument_node_id).join(m.instrument_type,
        m.instrument_type.c.instrument_type_id == m.instrument.c.instrument_type_id).where(
        m.instrument_type.c.type_code == kind, node.c.status == 'ACTIVE', visible_clause(node.c.reference_node_id, tenant))
    if route == 'LISTED':
        statement = statement.add_columns(m.listing.c.listing_node_id).join(m.listing,
            m.listing.c.instrument_node_id == m.instrument.c.instrument_node_id).where(visible_clause(m.listing.c.listing_node_id, tenant))
    if query.strip():
        escaped = query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        match = or_(node.c.canonical_name.ilike(f'%{escaped}%', escape='\\'), node.c.internal_code.ilike(f'%{escaped}%', escape='\\'),
            exists(select(1).select_from(m.financial_reference_identifier).where(
                m.financial_reference_identifier.c.reference_node_id == node.c.reference_node_id,
                m.financial_reference_identifier.c.identifier_value.ilike(f'%{escaped}%', escape='\\'))))
        if route == 'LISTED': match = or_(match, m.listing.c.trading_symbol.ilike(f'%{escaped}%', escape='\\'))
        statement = statement.where(match)
    total = connection.scalar(select(func.count()).select_from(statement.subquery()))
    ordering = [node.c.canonical_name, m.instrument.c.instrument_node_id]
    if route == 'LISTED': ordering.append(m.listing.c.listing_node_id)
    rows = connection.execute(statement.order_by(*ordering).limit(limit).offset(offset)).mappings()
    from .repository import RepositoryNotFound
    result = []
    for row in rows:
        try: result.append(load_context(connection, tenant, row.instrument_node_id, row.get('listing_node_id'), as_of))
        except RepositoryNotFound: continue
    return result, total


def book(connection, tenant, actor, request, key, kind, request_id):
    from .repository import _trade_booking_fingerprint, IdempotencyKeyConflict, RepositoryNotFound, get_booked_trade_detail, persist_trade_annotations
    from .trade_properties import validate_trade_annotations
    endpoint = '/v1/trades/' + {'STRUCTURED_PRODUCT': 'structured-products', 'FUTURE': 'futures', 'BOND': 'bonds', 'SWAP': 'swaps'}[kind]
    with connection.begin_nested():
        authorize_booking(connection, tenant, actor)
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            normalized = request.model_copy(update={'quantity': request.quantity.normalize(), 'execution_price': request.execution_price.normalize(), 'trade_datetime': request.trade_datetime.astimezone(timezone.utc),
                'accrued_interest_amount': request.accrued_interest_amount.normalize() if request.accrued_interest_amount is not None else None})
        fingerprint = _trade_booking_fingerprint(normalized, connection, tenant)
        existing = find_booking_replay(connection, tenant, endpoint, key, fingerprint)
        if existing:
            detail = get_booked_trade_detail(connection, tenant, existing, 'v1', request_id)
            if detail is None: raise RepositoryNotFound('Booked trade does not exist')
            return detail
        execution = request.trade_datetime.astimezone(timezone.utc)
        terms = load_context(connection, tenant, request.instrument_id, request.listing_id, execution.date(), True)
        if terms.kind != kind or not terms.booking_eligible: raise ProductBookingError(terms.ineligibility_message or 'Wrong booking product.')
        if terms.terms_fingerprint != request.expected_terms_fingerprint:
            raise ProductBookingError('Approved terms changed. Reselect for the execution date.', code='product.terms_changed')
        convention = terms.convention
        bond_details = None
        if kind != 'BOND' and any(value is not None for value in (request.price_type, request.accrued_interest_amount, request.settlement_evidence)):
            raise ProductBookingError('Bond-only fields are not accepted for this product.', 'priceType')
        if kind == 'BOND':
            if not request.price_type or request.accrued_interest_amount is None or not request.settlement_evidence or not request.settlement_evidence.strip():
                raise ProductBookingError('Confirm price type, total signed accrued interest (including zero) and settlement eligibility evidence.', 'settlementEvidence')
            if request.settlement_date is None or request.settlement_date >= terms.maturity_date:
                raise ProductBookingError('Actual bond settlement must precede maturity.', 'settlementDate')
            if terms.coupon_type == 'ZERO' and request.accrued_interest_amount != 0:
                raise ProductBookingError('Zero-coupon bonds require zero accrued interest.', 'accruedInterestAmount')
            try: clean, dirty = bond_amounts(request.quantity, request.execution_price, request.price_type, request.accrued_interest_amount)
            except ValueError as error: raise ProductBookingError(str(error), 'accruedInterestAmount') from error
            bond_details = dict(priceType=request.price_type, cleanAmount=decimal_text(clean), dirtyAmount=decimal_text(dirty),
                accruedInterestAmount=decimal_text(request.accrued_interest_amount), settlementEvidence=request.settlement_evidence.strip())
        if kind == 'FUTURE':
            if request.settlement_date is not None: raise ProductBookingError('Futures have no purchase settlement date.', 'settlementDate')
            if not request.position_effect: raise ProductBookingError('Record OPEN/CLOSE execution intent.', 'positionEffect')
            if execution > convention.last_trading_at_utc: raise ProductBookingError('Execution exceeds the approved trading cutoff.', 'tradeDatetime')
            if request.execution_price < 0 and not convention.allow_negative_price: raise ProductBookingError('Negative prices are not approved for this contract.', 'executionPrice')
            try:
                validate_increment(request.quantity, 1, minimum=1)
                validate_increment(request.execution_price, convention.tick_size)
            except ValueError as error: raise ProductBookingError(str(error), 'executionPrice' if request.quantity % 1 == 0 else 'quantity') from error
        elif kind == 'SWAP':
            if request.settlement_date is not None: raise ProductBookingError('Swap booking does not create a payment or settlement date.', 'settlementDate')
            if request.execution_route != 'OTC' or request.listing_id: raise ProductBookingError('Swap booking requires the OTC canonical contract.', 'executionRoute')
            if request.counterparty_organisation_id is None: raise ProductBookingError('Swap execution requires a counterparty.', 'counterpartyOrganisationId')
            try: validate_increment(request.quantity, convention.quantity_increment, minimum=convention.quantity_minimum)
            except ValueError as error: raise ProductBookingError(str(error), 'quantity') from error
        else:
            if request.position_effect is not None: raise ProductBookingError('Structured securities do not use futures execution intent.', 'positionEffect')
            if request.settlement_date is None: raise ProductBookingError('Enter the actual security settlement date.', 'settlementDate')
            if request.execution_price < 0: raise ProductBookingError('Security price must be non-negative.', 'executionPrice')
            if request.execution_route == 'OTC' and request.counterparty_organisation_id is None: raise ProductBookingError('OTC execution requires a counterparty.', 'counterpartyOrganisationId')
            try: validate_increment(request.quantity, convention.quantity_increment, minimum=convention.quantity_minimum)
            except ValueError as error: raise ProductBookingError(str(error), 'quantity') from error
        lock_booking_strategy(connection, tenant, request.strategy_id)
        annotations = validate_trade_annotations(connection, tenant, request)
        try:
            amount = swap_reference_value(request.quantity if request.side == 'BUY' else request.quantity.copy_negate(), request.execution_price, convention.quote_factor) if kind == 'SWAP' else execution_amount(request.quantity, request.execution_price, quantity_unit=convention.quantity_unit,
                price_basis=convention.price_basis, quote_factor=convention.quote_factor,
                denomination=getattr(convention, 'denomination', None), multiplier=getattr(convention, 'monetary_multiplier', None))
        except ValueError as error: raise ProductBookingError(str(error), 'executionPrice') from error
        trade_id = uuid4()
        venue = connection.scalar(select(m.listing.c.market_venue_id).where(m.listing.c.listing_node_id == request.listing_id)) if request.listing_id else None
        connection.execute(m.trade.insert().values(trade_id=trade_id, trade_subject_reference_node_id=request.listing_id or request.instrument_id,
            reference_instrument_node_id=request.instrument_id, strategy_id=request.strategy_id, trade_type='INVESTMENT',
            quantity=request.quantity if request.side == 'BUY' else request.quantity.copy_negate(), quantity_unit=convention.quantity_unit,
            execution_price=request.execution_price, price_basis=convention.price_basis, price_currency_id=convention.price_currency_id,
            position_effect=request.position_effect, trade_datetime_utc=execution, settlement_date=request.settlement_date,
            execution_venue_id=venue, execution_channel='MANUAL_UI', lifecycle_status='BOOKED', trade_purpose=request.trade_purpose,
            market_activity=request.market_activity, trader_person_id=request.trader_person_id,
            booked_by_user_account_id=actor, created_by_user_account_id=actor, comment=request.comment))
        persist_trade_annotations(connection, tenant, trade_id, request, annotations)
        economics = ProductTradeEconomicsView(terms=terms, amount=decimal_text(dirty if kind == 'BOND' else amount), bondDetails=bond_details,
            bookedNotional=request.quantity if kind == 'SWAP' and terms.swap_details.generic_terms else None,
            amountKind='ENTRY_REFERENCE_VALUE' if kind == 'SWAP' else 'REFERENCE_CONTRACT_VALUE' if kind == 'FUTURE' else 'CONSIDERATION',
            direction=None if kind in {'FUTURE', 'SWAP'} else ('PAY' if request.side == 'BUY' else 'RECEIVE'))
        connection.execute(m.trade_lifecycle_event.insert().values(trade_id=trade_id, sequence_no=1, event_type='BOOKED',
            event_datetime_utc=execution, source_event_id=key, payload_hash=fingerprint,
            event_payload=json.dumps({'schemaVersion': 1, 'kind': 'PRODUCT_BOOKING', 'economics': economics.model_dump(mode='json', by_alias=True)}, sort_keys=True),
            recorded_by_user_account_id=actor))
        record_booking_replay(connection, tenant, endpoint, key, fingerprint, trade_id)
        return get_booked_trade_detail(connection, tenant, trade_id, 'v1', request_id)


def load_economics(connection, trade_ids):
    if not trade_ids: return {}
    result = {}
    for trade_id, raw in connection.execute(select(m.trade_lifecycle_event.c.trade_id, m.trade_lifecycle_event.c.event_payload).where(
        m.trade_lifecycle_event.c.trade_id.in_(trade_ids), m.trade_lifecycle_event.c.sequence_no == 1, m.trade_lifecycle_event.c.event_type == 'BOOKED')):
        payload = json.loads(raw or '{}')
        if payload.get('kind') == 'PRODUCT_BOOKING' and payload.get('schemaVersion') == 1:
            result[trade_id] = ProductTradeEconomicsView.model_validate(payload['economics']).model_dump(mode='json', by_alias=True)
    return result

def materialize_family(connection, tenant, request):
    # Keep the governed underlying and crypto currency role stable through approval.
    for table, key, value in ((m.financial_reference_node, 'reference_node_id', request.underlying_id),
            (m.reference_node_scope, 'reference_node_id', request.underlying_id),
            (m.index_terms, 'index_node_id', request.underlying_id),
            (m.crypto_asset_terms, 'instrument_node_id', request.underlying_id),
            (m.currency, 'currency_id', request.contract_currency_id)):
        connection.execute(select(table).where(table.c[key] == value).with_for_update()).all()
    if request.specification and request.specification.contract_size_currency_id:
        connection.execute(select(m.currency).where(m.currency.c.currency_id == request.specification.contract_size_currency_id).with_for_update()).all()
    validate_family_references(connection, tenant, request.underlying_id, request.contract_currency_id, request.specification)
    code = f'FUTURE_FAMILY_{tenant.hex}_{request.family_code}'
    connection.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(code.encode()).digest()[:8], 'big', signed=True))))
    if connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code == code)):
        raise ProductBookingError('This tenant family code already exists. Select the approved family.')
    type_id = connection.scalar(select(m.reference_node_type.c.reference_node_type_id).where(
        m.reference_node_type.c.type_code == 'FUTURE_FAMILY', m.reference_node_type.c.status == 'ACTIVE'))
    if not type_id: raise ProductBookingError('Active futures-family catalogue is required.')
    node = connection.scalar(m.financial_reference_node.insert().values(reference_node_type_id=type_id,
        canonical_name=request.canonical_name, internal_code=code, is_tradable=False,
        status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
    connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,
        scope_type='TENANT_PRIVATE', owner_tenant_id=tenant, status='ACTIVE'))
    connection.execute(m.future_family.insert().values(family_node_id=node,
        underlying_reference_node_id=request.underlying_id, contract_currency_id=request.contract_currency_id,
        expiry_cycle=','.join(str(n) for n in request.specification.delivery_months) if request.specification else None,
        specification_payload=request.specification.model_dump_json(by_alias=True) if request.specification else None, status='ACTIVE'))
    return node


def search_families(connection, tenant, query, limit, offset):
    node = m.financial_reference_node
    underlying = node.alias('underlying')
    family = m.future_family
    prefix = f'FUTURE_FAMILY_{tenant.hex}_'
    statement = select(family, node.c.canonical_name, node.c.internal_code,
        underlying.c.canonical_name.label('underlying_name'), m.currency.c.currency_code).join(
        node, node.c.reference_node_id == family.c.family_node_id).join(
        underlying, underlying.c.reference_node_id == family.c.underlying_reference_node_id).join(
        m.currency, m.currency.c.currency_id == family.c.contract_currency_id).where(
        family.c.status == 'ACTIVE', node.c.status == 'ACTIVE', underlying.c.status == 'ACTIVE',
        m.currency.c.status == 'ACTIVE',
        node.c.internal_code.startswith(prefix, autoescape=True),
        visible_clause(node.c.reference_node_id, tenant), visible_clause(underlying.c.reference_node_id, tenant),
        exists(select(1).where(m.reference_node_scope.c.reference_node_id == node.c.reference_node_id,
            m.reference_node_scope.c.owner_tenant_id == tenant, m.reference_node_scope.c.scope_type == 'TENANT_PRIVATE',
            m.reference_node_scope.c.status == 'ACTIVE')))
    if query.strip():
        statement = statement.where(or_(node.c.canonical_name.icontains(query.strip(), autoescape=True),
                                        node.c.internal_code.icontains(query.strip(), autoescape=True)))
    total = connection.scalar(select(func.count()).select_from(statement.subquery()))
    rows = connection.execute(statement.order_by(node.c.canonical_name, family.c.future_family_id).limit(limit).offset(offset)).mappings()
    return [FutureFamilyView(familyId=r.future_family_id, familyNodeId=r.family_node_id,
        familyCode=r.internal_code[len(prefix):], canonicalName=r.canonical_name,
        underlyingId=r.underlying_reference_node_id, underlyingName=r.underlying_name,
        contractCurrencyId=r.contract_currency_id, currency=r.currency_code,
        specification=FutureFamilySpecification.model_validate_json(r.specification_payload) if r.specification_payload else None) for r in rows], total

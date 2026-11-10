"""Cash execution persistence and retained retry identities on a caller connection."""
from datetime import timezone
import hashlib
import json
from uuid import UUID, uuid4
from sqlalchemy import insert, select
from sqlalchemy.engine import Connection
from security_master_schema import models as m
from security_master_schema.errors import RepositoryNotFound
from .booking_contracts import TradeBookingRequest
from .recognition import trade_values, frozen_recognition

CASH_BOOKING_ENDPOINT = "/v1/trades"


def booking_fingerprint(payload: TradeBookingRequest, connection: Connection, tenant_id: UUID) -> str:
    data = payload.model_dump(mode="json", by_alias=True)
    # Omitted additive fields must not invalidate already-recorded retry keys.
    for field in ('priceType', 'accruedInterestAmount', 'settlementEvidence', 'correction', 'valuationEffectiveDate', 'valuationOverrideReason','profileAssignmentRevision'):
        if data.get(field) is None: data.pop(field, None)
    # Immutable definitions remain available after retirement, so replay can
    # canonicalise values without reapplying today's booking eligibility.
    from .annotations import normalize_property_value, TradeFieldError
    identifiers = [item.definition_id for item in payload.properties]
    definitions = {row["definition_id"]: row for row in connection.execute(
        select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id == tenant_id)
        .where(m.trade_property_definition.c.definition_id.in_(identifiers))
    ).mappings()} if identifiers else {}
    for item in data["properties"]:
        definition = definitions.get(UUID(item["definitionId"]))
        if definition is not None:
            try:
                item["value"] = normalize_property_value(item["value"], definition["value_type"], definition["choices"])
            except ValueError as error:
                raise TradeFieldError(f"properties.{item['definitionId']}", str(error)) from error
    enriched = {"executingBrokerOrganisationId":None, "traderPersonId":None, "tradePurpose":"INVESTMENT", "marketActivity":None, "tagIds":[], "properties":[], "externalReferences":[]}
    if all(data[key] == default for key, default in enriched.items()):
        for key in enriched: data.pop(key)
    else:
        data["tagIds"] = sorted(data["tagIds"])
        data["properties"] = sorted(data["properties"], key=lambda p:p["definitionId"])
        data["externalReferences"] = sorted(data["externalReferences"], key=lambda r:(r["referenceType"], r["sourceSystemId"] or "", r["referenceValue"]))
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def booking_idempotency_lock_key(tenant_id: UUID, idempotency_key: str) -> int:
    from security_master_schema.booking_controls import booking_lock_key
    return booking_lock_key(tenant_id, CASH_BOOKING_ENDPOINT, idempotency_key)


def persist_trade_annotations(connection, tenant_id, trade_id, request, annotation_values):
    """Shared persistence after tenant-governed annotations have been validated."""
    party_role_id = None
    if request.counterparty_organisation_id is not None:
        party_role_id = uuid4()
        connection.execute(insert(m.trade_party_role).values(trade_party_role_id=party_role_id, trade_id=trade_id, organisation_id=request.counterparty_organisation_id, role="COUNTERPARTY"))
    if request.external_reference:
        connection.execute(insert(m.trade_external_reference).values(trade_id=trade_id, trade_party_role_id=party_role_id, reference_type="SOURCE_TRADE_ID", reference_value=request.external_reference))
    if request.executing_broker_organisation_id:
        connection.execute(insert(m.trade_party_role).values(trade_id=trade_id, organisation_id=request.executing_broker_organisation_id, role="EXECUTING_BROKER"))
    for index, reference in enumerate(request.external_references):
        from sqlalchemy.exc import IntegrityError
        from security_master_schema.errors import TradeFieldError
        try:
            with connection.begin_nested():
                connection.execute(insert(m.trade_external_reference).values(trade_id=trade_id, reference_type=reference.reference_type, reference_value=reference.reference_value, source_system_id=reference.source_system_id))
        except IntegrityError as error:
            if getattr(getattr(error.orig, "diag", None), "constraint_name", None) != "uq_trade_external_reference_source_value": raise
            raise TradeFieldError(f"reference-{index}", "This source reference is already recorded. Check its namespace or value.") from error
    for prop in annotation_values:
        table = m.trade_property_reference if "record_version_id" in prop else m.trade_property_value
        connection.execute(insert(table).values(trade_id=trade_id, tenant_id=tenant_id, **prop))
    for tag_id in request.tag_ids:
        connection.execute(insert(m.trade_tag_assignment).values(trade_id=trade_id, tenant_id=tenant_id, tag_id=tag_id))


def insert_cash_execution(connection, tenant_id, actor_id, request, listing_row, strategy_id, annotation_values, fingerprint, idempotency_key,*,quantity_movement=None):
    """Persist the original execution, annotation rows and immutable BOOKED event."""
    from .profiles.validation import annotation_profile_values,annotation_event_proof
    trade_id = uuid4()
    signed_quantity = request.quantity if request.side == "BUY" else request.quantity.copy_negate()
    trade_datetime_utc = request.trade_datetime.astimezone(timezone.utc)
    connection.execute(
        insert(m.trade).values(
            trade_id=trade_id,
            trade_subject_reference_node_id=listing_row["listing_node_id"],
            reference_instrument_node_id=listing_row["instrument_node_id"],
            strategy_id=strategy_id,
            trade_type=quantity_movement['kind'] if quantity_movement else "INVESTMENT",
            trade_purpose=request.trade_purpose,
            market_activity=request.market_activity,
            trader_person_id=request.trader_person_id,
            execution_price=request.execution_price,
            price_basis="UNIT_PRICE",
            price_currency_id=listing_row["trading_currency_id"],
            quantity=signed_quantity,
            quantity_unit=listing_row['booking_snapshot']['quantityUnit'],
            trade_datetime_utc=trade_datetime_utc,
            **trade_values(request),
            **annotation_profile_values(annotation_values),
            settlement_date=request.settlement_date,
            booked_by_user_account_id=actor_id,
            execution_channel="MANUAL_UI",
            execution_venue_id=listing_row["market_venue_id"],
            lifecycle_status="BOOKED",
            created_by_user_account_id=actor_id,
            comment=request.comment,
        )
    )
    snapshot=listing_row['booking_snapshot'] | frozen_recognition(request) | annotation_event_proof(annotation_values)
    if quantity_movement:snapshot['quantityMovement']=quantity_movement
    connection.execute(insert(m.trade_lifecycle_event).values(trade_id=trade_id, sequence_no=1, event_type="BOOKED", event_datetime_utc=trade_datetime_utc, source_event_id=idempotency_key, payload_hash=fingerprint, event_payload=json.dumps(snapshot, sort_keys=True), recorded_by_user_account_id=actor_id))
    persist_trade_annotations(connection, tenant_id, trade_id, request, annotation_values)
    return trade_id


def require_owned_execution(connection, tenant_id, strategy_id, trade_id):
    """A replay identity must still refer to this tenant and requested strategy.

    Retired references/strategies remain replayable; today's write authority is
    checked by the command before this historical-ownership check.
    """
    row=connection.scalar(select(m.trade.c.trade_id).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id).where(
        m.trade.c.trade_id==trade_id,m.strategy.c.tenant_id==tenant_id,m.trade.c.strategy_id==strategy_id))
    if row is None: raise RepositoryNotFound("Booked trade does not exist")

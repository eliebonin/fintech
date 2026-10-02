"""Tenant trade catalogue, typed annotation validation and eligible people."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
import hashlib
from uuid import uuid4, UUID
from sqlalchemy import select, insert, func, or_
from security_master_schema import models as m
from security_master_schema.tenant_workspace import require_tenant_action, resolve_tenant_workspace

class TradeFieldError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field

def normalize_property_value(value, kind, choices):
    if kind == "BOOLEAN":
        if type(value) is not bool: raise ValueError("Select true or false.")
        return value
    if not isinstance(value, str): raise ValueError("A text value is required.")
    value = value.strip()
    if not value: raise ValueError("A value is required.")
    if kind == "INTEGER":
        if not re.fullmatch(r"[+-]?\d{1,30}", value): raise ValueError("Enter an integer of at most 30 digits.")
        return str(int(value))
    if kind == "REFERENCE":
        return str(UUID(value))
    if kind == "TEXT":
        if len(value) > 2000: raise ValueError("Text must be at most 2000 characters.")
        return value
    if kind == "CHOICE":
        # Historical detail/replay only; new dropdowns require governed references.
        if value not in choices: raise ValueError("Select an allowed choice.")
        return value
    if kind == "DATE":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value): raise ValueError("Use YYYY-MM-DD.")
        return date.fromisoformat(value).isoformat()
    if kind == "DECIMAL":
        if len(value) > 80 or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value): raise ValueError("Enter a finite decimal without exponents.")
        number = Decimal(value)
        fraction = value.partition(".")[2].rstrip("0")
        integer = value.lstrip("+-").partition(".")[0].lstrip("0")
        if len(fraction) > 12 or len(integer) > 18: raise ValueError("Decimal exceeds precision 30/scale 12.")
        result = format(number, "f").rstrip("0").rstrip(".") if "." in value else format(number, "f")
        return "0" if number == 0 else result.lstrip("+")
    raise ValueError("Unsupported property type.")

def assert_trade_writer(connection, tenant_id, actor_id):
    require_tenant_action(resolve_tenant_workspace(connection, tenant_id, actor_id, date.today()), "TRADE_WRITE")

def provision_trade_catalogue(connection, tenant_id, actor_id, definitions, tags):
    """Idempotently provision immutable definitions; never silently overwrite."""
    assert_trade_writer(connection, tenant_id, actor_id)
    lock_trade_catalogue(connection, tenant_id)
    reserved = {"counterparty", "counterpartyorganisationid", "trader", "traderpersonid", "quantity", "executionprice", "settlementdate", "listingid", "strategyid", "instrument", "maturity", "strike", "broker"}
    for table, items in ((m.trade_property_definition, definitions), (m.trade_tag, tags)):
        active = connection.scalar(select(func.count()).select_from(table).where(table.c.tenant_id == tenant_id, table.c.status == "ACTIVE"))
        codes = set()
        validated = []
        for item in items:
            code = item.get("code", "").strip().upper()
            label = item.get("label", "").strip()
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", code) or code.lower().replace("_", "") in reserved or code in codes: raise ValueError("Invalid, reserved or duplicate catalogue code.")
            if not label or len(label) > 250: raise ValueError("A label of at most 250 characters is required.")
            codes.add(code)
            values = dict(code=code, label=label)
            if table is m.trade_property_definition:
                kind = item.get("valueType")
                if kind == "CHOICE":
                    raise ValueError("Embedded choices are historical only; use a REFERENCE field with a governed catalogue.")
                choices = item.get("choices", [])
                required = item.get("required", False)
                if kind not in {"TEXT", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "REFERENCE"} or type(required) is not bool: raise ValueError("Invalid property type or required flag.")
                if choices != []: raise ValueError("Embedded choices are not supported; bind a governed catalogue instead.")
                values.update(value_type=kind, required=required, choices=choices, description=item.get("description"), version_no=item.get("versionNo", 1), sort_order=item.get("sortOrder", 0))
                catalogue_id = item.get("catalogueId")
                if (kind == "REFERENCE") != bool(catalogue_id): raise ValueError("Reference fields require a catalogue; scalar fields cannot bind one.")
                if catalogue_id:
                    from .governed_trade_configuration import find_catalogue
                    if find_catalogue(connection, tenant_id, catalogue_id)["status"] != "ACTIVE": raise ValueError("Publish the catalogue before using it.")
                    if required and not connection.scalar(select(m.reference_catalogue_record.c.record_version_id).where(m.reference_catalogue_record.c.catalogue_id == catalogue_id, m.reference_catalogue_record.c.status == "ACTIVE").limit(1)):
                        raise ValueError("A required reference field needs at least one selectable catalogue entry.")
                values["catalogue_id"] = catalogue_id
            existing = connection.execute(select(table).where(table.c.tenant_id == tenant_id, table.c.code == code, table.c.status == "ACTIVE")).mappings().first()
            if existing:
                if any(existing[key] != value for key, value in values.items()): raise ValueError("Catalogue meaning cannot be overwritten; retire and provision a new version.")
            else: validated.append(values)
        if active + len(validated) > 1000: raise ValueError("The alpha safety quota is 1000 active items; it is not a fixed set of field slots.")
        # Validate each catalogue before insert; callers wrap provisioning in a transaction.
        for values in validated:
            connection.execute(insert(table).values(**values, tenant_id=tenant_id, created_by_user_account_id=actor_id))

def list_trade_traders(connection, tenant_id, query="", limit=100, curated=True):
    person, account, member = m.person, m.user_account, m.tenant_user_account
    today = date.today()
    statement = select(person.c.person_id, person.c.display_name).select_from(person.join(account, account.c.person_id == person.c.person_id).join(member, member.c.user_account_id == account.c.user_account_id)).where(person.c.status == "ACTIVE", account.c.status == "ACTIVE", member.c.tenant_id == tenant_id, member.c.status == "ACTIVE", member.c.valid_from <= today, or_(member.c.valid_to.is_(None), member.c.valid_to >= today)).distinct()
    if query: statement = statement.where(func.lower(person.c.display_name).contains(query.lower(), autoescape=True))
    from .governed_trade_configuration import restrict_selection
    if curated: statement = restrict_selection(connection, tenant_id, "TRADER", statement, person.c.person_id)
    return [{"personId": row.person_id, "displayName": row.display_name} for row in connection.execute(statement.order_by(person.c.display_name, person.c.person_id).limit(limit))]

def get_trade_booking_context(connection, tenant_id, actor_id):
    assert_trade_writer(connection, tenant_id, actor_id)
    definitions = connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id == tenant_id, m.trade_property_definition.c.status == "ACTIVE", m.trade_property_definition.c.value_type != "CHOICE").order_by(m.trade_property_definition.c.sort_order, m.trade_property_definition.c.code)).mappings().all()
    tags = connection.execute(select(m.trade_tag).where(m.trade_tag.c.tenant_id == tenant_id, m.trade_tag.c.status == "ACTIVE").order_by(m.trade_tag.c.label)).mappings().all()
    return dict(tenantId=tenant_id, bookedByUserAccountId=actor_id, properties=[dict(definitionId=r.definition_id, code=r.code, label=r.label, valueType=r.value_type, required=r.required, choices=r.choices, description=r.description, catalogueId=r.catalogue_id) for r in definitions], tags=[dict(tagId=r.tag_id, code=r.code, label=r.label) for r in tags])

def lock_trade_catalogue(connection, tenant_id):
    key = int.from_bytes(hashlib.sha256(f"trade-catalogue:{tenant_id}".encode()).digest()[:8], "big", signed=True)
    connection.execute(select(func.pg_advisory_xact_lock(key)))

def validate_trade_annotations(connection, tenant_id, request):
    lock_trade_catalogue(connection, tenant_id)
    definitions = {r.definition_id:r for r in connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id == tenant_id, m.trade_property_definition.c.status == "ACTIVE").order_by(m.trade_property_definition.c.definition_id).with_for_update()).mappings()}
    supplied = {p.definition_id:p for p in request.properties}
    for identifier, definition in definitions.items():
        if definition.required and identifier not in supplied: raise TradeFieldError(f"properties.{identifier}", f"{definition.label} is required.")
    values = []
    for prop in request.properties:
        definition = definitions.get(prop.definition_id)
        if definition is None: raise TradeFieldError(f"properties.{prop.definition_id}", "Property is unavailable in this tenant.")
        if definition.value_type == "CHOICE": raise TradeFieldError(f"properties.{prop.definition_id}", "Legacy dropdown has been replaced. Reopen the booking ticket.")
        try: value = normalize_property_value(prop.value, definition.value_type, definition.choices)
        except ValueError as exc: raise TradeFieldError(f"properties.{prop.definition_id}", str(exc)) from exc
        if definition.value_type == "REFERENCE":
            from .governed_trade_configuration import validate_reference
            try: validate_reference(connection, tenant_id, definition.catalogue_id, UUID(value))
            except ValueError as exc: raise TradeFieldError(f"properties.{prop.definition_id}", str(exc)) from exc
            values.append(dict(definition_id=prop.definition_id, record_version_id=UUID(value)))
        else: values.append(dict(definition_id=prop.definition_id, value=value))
    tags = connection.execute(select(m.trade_tag.c.tag_id).where(m.trade_tag.c.tenant_id == tenant_id, m.trade_tag.c.status == "ACTIVE", m.trade_tag.c.tag_id.in_(request.tag_ids)).order_by(m.trade_tag.c.tag_id).with_for_update()).scalars().all()
    if set(tags) != set(request.tag_ids): raise TradeFieldError("tagIds", "A tag is unavailable in this tenant.")
    for field, organisation_id in (("counterpartyOrganisationId", request.counterparty_organisation_id), ("executingBrokerOrganisationId", request.executing_broker_organisation_id)):
        if organisation_id is not None and not connection.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.organisation_id == organisation_id, m.organisation.c.status == "ACTIVE").with_for_update()): raise TradeFieldError(field, "Select an active shared organisation.")
        if organisation_id is not None:
            from .governed_trade_configuration import assert_selection
            assert_selection(connection, tenant_id, "COUNTERPARTY" if field == "counterpartyOrganisationId" else "EXECUTING_BROKER", organisation_id, field)
    if request.trader_person_id:
        person, account, member = m.person, m.user_account, m.tenant_user_account
        today = date.today()
        eligible = connection.scalar(select(person.c.person_id).select_from(person.join(account, account.c.person_id == person.c.person_id).join(member, member.c.user_account_id == account.c.user_account_id)).where(person.c.person_id == request.trader_person_id, person.c.status == "ACTIVE", account.c.status == "ACTIVE", member.c.tenant_id == tenant_id, member.c.status == "ACTIVE", member.c.valid_from <= today, or_(member.c.valid_to.is_(None), member.c.valid_to >= today)).limit(1).with_for_update())
        if eligible is None: raise TradeFieldError("traderPersonId", "Select an active person linked to this tenant's membership.")
        from .governed_trade_configuration import assert_selection
        assert_selection(connection, tenant_id, "TRADER", request.trader_person_id, "traderPersonId")
    # Preserve global source-namespace identity; never reveal another tenant's trade.
    for index, reference in sorted(enumerate(request.external_references), key=lambda entry:(entry[1].source_system_id or "", entry[1].reference_type, entry[1].reference_value)):
        if reference.source_system_id is None: continue
        scope = repr((reference.source_system_id, reference.reference_type, reference.reference_value))
        lock = int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], "big", signed=True)
        connection.execute(select(func.pg_advisory_xact_lock(lock)))
        external = m.trade_external_reference
        if connection.scalar(select(external.c.trade_external_reference_id).where(external.c.source_system_id == reference.source_system_id, external.c.reference_type == reference.reference_type, external.c.reference_value == reference.reference_value).limit(1)):
            raise TradeFieldError(f"reference-{index}", "This source reference is already recorded. Check its namespace or value.")
    return values

def read_trade_annotations(connection, tenant_id, trade_id):
    from .contracts import TradePropertyValueView, TradeTagView
    definition, value = m.trade_property_definition, m.trade_property_value
    rows = connection.execute(select(definition, value.c.value).select_from(value.join(definition, value.c.definition_id == definition.c.definition_id)).where(value.c.trade_id == trade_id, value.c.tenant_id == tenant_id, definition.c.tenant_id == tenant_id).order_by(definition.c.sort_order, definition.c.code)).mappings().all()
    properties = [TradePropertyValueView(definitionId=r.definition_id, code=r.code, label=r.label, valueType=r.value_type, required=r.required, choices=r.choices, description=r.description, value=r.value) for r in rows]
    reference, record = m.trade_property_reference, m.reference_catalogue_record
    rows = connection.execute(select(definition, record.c.record_version_id, record.c.label.label("record_label"), record.c.code.label("record_code"), record.c.version_no.label("record_version"))
        .select_from(reference.join(definition, reference.c.definition_id == definition.c.definition_id).join(record, reference.c.record_version_id == record.c.record_version_id))
        .where(reference.c.tenant_id == tenant_id, reference.c.trade_id == trade_id, definition.c.tenant_id == tenant_id)).mappings()
    properties.extend(TradePropertyValueView(definitionId=r.definition_id, code=r.code, label=r.label, valueType=r.value_type, required=r.required, choices=r.choices, description=r.description,
        catalogueId=r.catalogue_id, value=str(r.record_version_id), displayValue=f"{r.record_code} — {r.record_label}", recordVersion=r.record_version) for r in rows)
    tag, assignment = m.trade_tag, m.trade_tag_assignment
    rows = connection.execute(select(tag).join(assignment, tag.c.tag_id == assignment.c.tag_id).where(assignment.c.trade_id == trade_id, assignment.c.tenant_id == tenant_id, tag.c.tenant_id == tenant_id).order_by(tag.c.label)).mappings().all()
    return properties, [TradeTagView(tagId=r.tag_id, code=r.code, label=r.label) for r in rows]

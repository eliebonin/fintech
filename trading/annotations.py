"""Tenant-governed booking values, catalogue locks and role eligibility.

Read/configuration views remain in the API; these are the original validators.
"""
from datetime import date
from decimal import Decimal
import hashlib
import re
from uuid import UUID
from sqlalchemy import select, func, or_
from security_master_schema import models as m
from security_master_schema.errors import TradeFieldError
from security_master_schema.governance_clock import governance_date


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


def lock_trade_catalogue(connection, tenant_id):
    from security_master_schema.booking_controls import lock_trade_configuration
    lock_trade_configuration(connection,tenant_id)


def validate_trade_annotations(connection, tenant_id, request, *, actor_id=None, configuration=None, operation='TRADE_WRITE', native_required=(),source_trade_ids=()):
    lock_trade_catalogue(connection, tenant_id)
    from .profiles.validation import annotation_context,ProfiledAnnotations
    configuration=annotation_context(connection,tenant_id,request,actor_id,configuration,operation,native_required)
    custom=[field for field in configuration['fields'] if field['definitionId'] is not None]
    from .profiles.inheritance import request_sources
    original_values,_=request_sources(connection,tenant_id,actor_id,request)
    original_options={identity:(value,) for identity,value in original_values.items()}
    if source_trade_ids:
        if operation not in {'LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE'}:
            raise ValueError('Source inheritance is restricted to supported lifecycle commands.')
        from .profiles.inheritance import lifecycle_sources
        original_options=lifecycle_sources(connection,tenant_id,request.strategy_id,source_trade_ids,configuration)

    allowed={field['definitionId'] for field in custom if field['requirement']!='NOT_USED'}|set(original_options)
    required={field['definitionId']:field['label'] for field in custom if field['requirement']=='REQUIRED'}
    definitions = {r.definition_id:r for r in connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id == tenant_id,m.trade_property_definition.c.definition_id.in_(allowed)).order_by(m.trade_property_definition.c.definition_id).with_for_update()).mappings()}
    from .profiles.resolution import definition_available
    family=connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant_id,m.trade_property_definition.c.code.in_([r.code for r in definitions.values()]))).mappings().all()
    supplied = {p.definition_id:p for p in request.properties}
    for identifier,label in required.items():
        if identifier not in supplied: raise TradeFieldError(f"properties.{identifier}", f"{label} is required.")
    values = ProfiledAnnotations(configuration)
    preserved=[]
    for prop in request.properties:
        definition = definitions.get(prop.definition_id)
        if definition is None: raise TradeFieldError(f"properties.{prop.definition_id}", "Property is unavailable in the assigned trade profile.")
        unchanged=any(original.value==prop.value for original in original_options.get(prop.definition_id,()))
        if not unchanged and not definition_available(definition,family): raise TradeFieldError(f"properties.{prop.definition_id}", "The pinned definition is retired; review the assigned profile.")
        if definition.value_type == "CHOICE" and not unchanged: raise TradeFieldError(f"properties.{prop.definition_id}", "Legacy dropdown has been replaced. Reopen the booking ticket.")
        try: value = normalize_property_value(prop.value, definition.value_type, definition.choices)
        except ValueError as exc: raise TradeFieldError(f"properties.{prop.definition_id}", str(exc)) from exc
        if unchanged:value=prop.value
        if prop.definition_id not in {field['definitionId'] for field in custom if field['requirement']!='NOT_USED'} and not unchanged:
            raise TradeFieldError(f"properties.{prop.definition_id}","Only the original unchanged value can be carried from a field not used by this profile.")
        if unchanged:preserved.append(str(prop.definition_id))
        if definition.value_type == "REFERENCE":
            try: validate_reference(connection, tenant_id, definition.catalogue_id, UUID(value),allow_inactive=unchanged)
            except ValueError as exc: raise TradeFieldError(f"properties.{prop.definition_id}", str(exc)) from exc
            values.append(dict(definition_id=prop.definition_id, record_version_id=UUID(value)))
        else: values.append(dict(definition_id=prop.definition_id, value=value))
    values.source_preservation=({'sourceTradeIds':sorted(map(str,source_trade_ids)),'definitionIds':sorted(preserved)} if source_trade_ids else dict(originalTradeId=str(request.correction.trade_id),definitionIds=sorted(preserved))) if preserved else None
    tags = connection.execute(select(m.trade_tag.c.tag_id).where(m.trade_tag.c.tenant_id == tenant_id, m.trade_tag.c.status == "ACTIVE", m.trade_tag.c.tag_id.in_(request.tag_ids)).order_by(m.trade_tag.c.tag_id).with_for_update()).scalars().all()
    if set(tags) != set(request.tag_ids): raise TradeFieldError("tagIds", "A tag is unavailable in this tenant.")
    parties = (("counterpartyOrganisationId", request.counterparty_organisation_id), ("executingBrokerOrganisationId", request.executing_broker_organisation_id))
    # Tenant-local catalogue locks do not serialize globally shared party rows.
    active_parties = set()
    for organisation_id in sorted({identifier for _, identifier in parties if identifier is not None}, key=str):
        if connection.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.organisation_id == organisation_id, m.organisation.c.status == "ACTIVE").with_for_update()):
            active_parties.add(organisation_id)
    for field, organisation_id in parties:
        if organisation_id is not None and organisation_id not in active_parties: raise TradeFieldError(field, "Select an active shared organisation.")
        if organisation_id is not None:
            assert_selection(connection, tenant_id, "COUNTERPARTY" if field == "counterpartyOrganisationId" else "EXECUTING_BROKER", organisation_id, field)
    if request.trader_person_id:
        person, account, member = m.person, m.user_account, m.tenant_user_account
        today = governance_date()
        eligible = connection.scalar(select(person.c.person_id).select_from(person.join(account, account.c.person_id == person.c.person_id).join(member, member.c.user_account_id == account.c.user_account_id)).where(person.c.person_id == request.trader_person_id, person.c.status == "ACTIVE", account.c.status == "ACTIVE", member.c.tenant_id == tenant_id, member.c.status == "ACTIVE", member.c.valid_from <= today, or_(member.c.valid_to.is_(None), member.c.valid_to >= today)).limit(1).with_for_update())
        if eligible is None: raise TradeFieldError("traderPersonId", "Select an active person linked to this tenant's membership.")
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


def validate_reference(connection, tenant_id, catalogue_id, record_version_id,*,allow_inactive=False):
    record, catalogue = m.reference_catalogue_record, m.reference_catalogue
    statement=select(record.c.record_version_id).join(catalogue, record.c.catalogue_id == catalogue.c.catalogue_id).where(
        record.c.record_version_id == record_version_id, catalogue.c.catalogue_id == catalogue_id, catalogue.c.tenant_id == tenant_id,
        *([] if allow_inactive else [catalogue.c.status == "ACTIVE", record.c.status == "ACTIVE"])).with_for_update()
    if not connection.scalar(statement):
        raise ValueError("Select an active record from this field's tenant catalogue.")


def restrict_selection(connection, tenant_id, role, statement, identity_column):
    policy = m.trade_selection_policy
    if connection.scalar(select(policy.c.version_no).where(policy.c.tenant_id == tenant_id, policy.c.role == role)) is not None:
        member = m.trade_selection_member
        column = member.c.person_id if role == "TRADER" else member.c.organisation_id
        statement = statement.where(identity_column.in_(select(column).where(member.c.tenant_id == tenant_id, member.c.role == role)))
    return statement


def assert_selection(connection, tenant_id, role, identifier, field):
    policy, member = m.trade_selection_policy, m.trade_selection_member
    if connection.scalar(select(policy.c.version_no).where(policy.c.tenant_id == tenant_id, policy.c.role == role)) is None: return
    column = member.c.person_id if role == "TRADER" else member.c.organisation_id
    if not connection.scalar(select(member.c.member_id).where(member.c.tenant_id == tenant_id, member.c.role == role, column == identifier)):
        raise TradeFieldError(field, "This record is not eligible for this tenant and trade role.")

"""Small, tenant-owned reference-data domain; no arbitrary source adapters."""
from datetime import datetime, timezone
import re
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update, delete, func
from security_master_schema import models as m
from .trade_properties import assert_trade_configurator, lock_trade_catalogue, TradeFieldError
from .trade_configuration import ConfigurationConflict

def audit(connection, tenant_id, actor_id, action, subject_id, reason, payload=None):
    if not reason.strip() or len(reason) > 2000: raise ValueError("A reason of at most 2000 characters is required.")
    connection.execute(insert(m.trade_configuration_event).values(tenant_id=tenant_id, actor_id=actor_id, action=action,
        subject_id=subject_id, reason=reason.strip(), payload=payload or {}))

def text_values(values):
    code = values.get("code", "").strip().upper()
    label = values.get("label", "").strip()
    description = (values.get("description") or "").strip() or None
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", code): raise ValueError("Use a code starting with a letter, then letters, digits or underscores.")
    if not label or len(label) > 250: raise ValueError("A label of at most 250 characters is required.")
    if description and len(description) > 2000: raise ValueError("Description exceeds 2000 characters.")
    return dict(code=code, label=label, description=description)

def find_catalogue(connection, tenant_id, catalogue_id):
    row = connection.execute(select(m.reference_catalogue).where(m.reference_catalogue.c.tenant_id == tenant_id,
        m.reference_catalogue.c.catalogue_id == catalogue_id).with_for_update()).mappings().first()
    if row is None: raise LookupError("Catalogue not found in this tenant.")
    return row

def catalogue_view(row):
    return dict(catalogueId=row["catalogue_id"], code=row["code"], label=row["label"], description=row["description"], status=row["status"])

def record_view(row):
    return dict(recordVersionId=row["record_version_id"], recordId=row["record_id"], code=row["code"], label=row["label"],
                description=row["description"], versionNo=row["version_no"], status=row["status"])

def create_catalogue(connection, tenant_id, actor_id, values):
    assert_trade_configurator(connection, tenant_id, actor_id); lock_trade_catalogue(connection, tenant_id)
    data = text_values(values)
    table = m.reference_catalogue
    row = connection.execute(select(table).where(table.c.tenant_id == tenant_id, table.c.code == data["code"])).mappings().first()
    if row:
        if any(row[k] != v for k, v in data.items()): raise ConfigurationConflict("Catalogue code already exists with a different definition.")
        return catalogue_view(row)
    identifier = uuid4()
    audit(connection, tenant_id, actor_id, "CATALOGUE_CREATED", identifier, values["reason"])
    connection.execute(insert(table).values(catalogue_id=identifier, tenant_id=tenant_id, created_by_user_account_id=actor_id, **data))
    return catalogue_view(find_catalogue(connection, tenant_id, identifier))

def catalogue_lifecycle(connection, tenant_id, actor_id, catalogue_id, status, reason):
    assert_trade_configurator(connection, tenant_id, actor_id); lock_trade_catalogue(connection, tenant_id)
    row = find_catalogue(connection, tenant_id, catalogue_id)
    if row["status"] == status: return catalogue_view(row)
    if row["status"] == "RETIRED": raise ConfigurationConflict("Retired catalogues cannot be republished.")
    if status == "RETIRED" and connection.scalar(select(func.count()).select_from(m.trade_property_definition).where(
        m.trade_property_definition.c.catalogue_id == catalogue_id, m.trade_property_definition.c.status == "ACTIVE")):
        raise ConfigurationConflict("Retire or replace all active fields using this catalogue first.")
    if status not in {"ACTIVE", "RETIRED"}: raise ValueError("Unsupported lifecycle action.")
    changes = {"status": status}
    if status == "RETIRED": changes.update(retired_by_user_account_id=actor_id, retired_at_utc=datetime.now(timezone.utc))
    audit(connection, tenant_id, actor_id, "CATALOGUE_" + status, catalogue_id, reason)
    connection.execute(update(m.reference_catalogue).where(m.reference_catalogue.c.catalogue_id == catalogue_id).values(**changes))
    return catalogue_view(find_catalogue(connection, tenant_id, catalogue_id))

def list_catalogues(connection, tenant_id, actor_id, q="", offset=0, limit=25):
    assert_trade_configurator(connection, tenant_id, actor_id)
    table = m.reference_catalogue
    statement = select(table).where(table.c.tenant_id == tenant_id)
    if q: statement = statement.where(func.lower(table.c.label + " " + table.c.code).contains(q.lower(), autoescape=True))
    return [catalogue_view(r) for r in connection.execute(statement.order_by(table.c.code).offset(offset).limit(limit)).mappings()]

def get_catalogue(connection, tenant_id, actor_id, catalogue_id):
    assert_trade_configurator(connection, tenant_id, actor_id)
    return catalogue_view(find_catalogue(connection, tenant_id, catalogue_id))

def list_records(connection, tenant_id, actor_id, catalogue_id, q="", offset=0, limit=25, history=False):
    assert_trade_configurator(connection, tenant_id, actor_id)
    catalogue = find_catalogue(connection, tenant_id, catalogue_id)
    if not history and catalogue["status"] != "ACTIVE": return []
    table = m.reference_catalogue_record
    statement = select(table).where(table.c.catalogue_id == catalogue_id)
    if not history: statement = statement.where(table.c.status == "ACTIVE")
    if q: statement = statement.where(func.lower(table.c.label + " " + table.c.code).contains(q.lower(), autoescape=True))
    return [record_view(r) for r in connection.execute(statement.order_by(table.c.code, table.c.version_no.desc()).offset(offset).limit(limit)).mappings()]

def create_record(connection, tenant_id, actor_id, catalogue_id, values):
    assert_trade_configurator(connection, tenant_id, actor_id); lock_trade_catalogue(connection, tenant_id)
    if find_catalogue(connection, tenant_id, catalogue_id)["status"] == "RETIRED": raise ConfigurationConflict("Catalogue is retired.")
    data = text_values(values)
    table = m.reference_catalogue_record
    old = connection.execute(select(table).where(table.c.catalogue_id == catalogue_id, table.c.code == data["code"]).order_by(table.c.version_no.desc())).mappings().first()
    if old:
        if old["status"] == "ACTIVE" and all(old[k] == v for k,v in data.items()): return record_view(old)
        raise ConfigurationConflict("This code is already used. Correct its label through a new version, or use a new code for a new meaning.")
    identifier = uuid4()
    audit(connection, tenant_id, actor_id, "RECORD_PUBLISHED", identifier, values["reason"])
    row = connection.execute(insert(table).values(catalogue_id=catalogue_id, record_id=uuid4(), record_version_id=identifier,
        created_by_user_account_id=actor_id, **data).returning(table)).mappings().one()
    return record_view(row)

def change_record(connection, tenant_id, actor_id, catalogue_id, record_version_id, values=None, reason=""):
    assert_trade_configurator(connection, tenant_id, actor_id); lock_trade_catalogue(connection, tenant_id)
    if find_catalogue(connection, tenant_id, catalogue_id)["status"] == "RETIRED": raise ConfigurationConflict("Catalogue is retired.")
    table = m.reference_catalogue_record
    old = connection.execute(select(table).where(table.c.catalogue_id == catalogue_id, table.c.record_version_id == record_version_id).with_for_update()).mappings().first()
    if old is None: raise LookupError("Record not found in this tenant catalogue.")
    if old["status"] != "ACTIVE":
        if values is None: return record_view(old)
        data = text_values({**values, "code": old["code"]})
        successor = connection.execute(select(table).where(table.c.record_id == old["record_id"], table.c.version_no == old["version_no"] + 1)).mappings().first()
        if successor and successor["status"] == "ACTIVE" and all(successor[k] == v for k,v in data.items()): return record_view(successor)
        raise ConfigurationConflict("This record has changed. Reload before editing.")
    data = text_values({**values, "code": old["code"]}) if values else None
    if data is None:
        active_count = connection.scalar(select(func.count()).select_from(table).where(table.c.catalogue_id == catalogue_id, table.c.status == "ACTIVE"))
        required_binding = connection.scalar(select(func.count()).select_from(m.trade_property_definition).where(m.trade_property_definition.c.catalogue_id == catalogue_id, m.trade_property_definition.c.status == "ACTIVE", m.trade_property_definition.c.required.is_(True)))
        if active_count <= 1 and required_binding: raise ConfigurationConflict("Replace or retire required fields before retiring their last selectable entry.")
    audit(connection, tenant_id, actor_id, "RECORD_CORRECTED" if data else "RECORD_RETIRED", old["record_id"], reason)
    connection.execute(update(table).where(table.c.record_version_id == record_version_id).values(status="RETIRED", retired_by_user_account_id=actor_id, retired_at_utc=datetime.now(timezone.utc)))
    if data:
        row = connection.execute(insert(table).values(catalogue_id=catalogue_id, record_id=old["record_id"], version_no=old["version_no"]+1,
            created_by_user_account_id=actor_id, **data).returning(table)).mappings().one()
        return record_view(row)
    return record_view({**old, "status":"RETIRED"})

def validate_reference(connection, tenant_id, catalogue_id, record_version_id):
    record, catalogue = m.reference_catalogue_record, m.reference_catalogue
    if not connection.scalar(select(record.c.record_version_id).join(catalogue, record.c.catalogue_id == catalogue.c.catalogue_id).where(
        record.c.record_version_id == record_version_id, catalogue.c.catalogue_id == catalogue_id, catalogue.c.tenant_id == tenant_id,
        catalogue.c.status == "ACTIVE", record.c.status == "ACTIVE").with_for_update()):
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

def selection_view(connection, tenant_id, actor_id, role):
    assert_trade_configurator(connection, tenant_id, actor_id)
    policy, member = m.trade_selection_policy, m.trade_selection_member
    row = connection.execute(select(policy).where(policy.c.tenant_id == tenant_id, policy.c.role == role)).mappings().first()
    entity = m.person if role == "TRADER" else m.organisation
    key = entity.c.person_id if role == "TRADER" else entity.c.organisation_id
    target = member.c.person_id if role == "TRADER" else member.c.organisation_id
    records = connection.execute(select(key, entity.c.display_name).join(member, key == target).where(member.c.tenant_id == tenant_id, member.c.role == role).order_by(entity.c.display_name)).all()
    return dict(role=role, versionNo=row["version_no"] if row else 0, mode="CURATED" if row else "LEGACY", records=[dict(id=str(r[0]), label=r[1]) for r in records])

def publish_selection(connection, tenant_id, actor_id, role, identifiers, expected_version, reason):
    assert_trade_configurator(connection, tenant_id, actor_id); lock_trade_catalogue(connection, tenant_id)
    if role not in {"COUNTERPARTY", "EXECUTING_BROKER", "TRADER"}: raise ValueError("Unsupported trade role.")
    if len(set(identifiers)) != len(identifiers) or len(identifiers) > 1000: raise ValueError("Use at most 1000 distinct eligible records.")
    if not reason.strip() or len(reason) > 2000: raise ValueError("A reason of at most 2000 characters is required.")
    current = selection_view(connection, tenant_id, actor_id, role)
    if current["versionNo"] != expected_version:
        if current["versionNo"] == expected_version + 1 and {str(i) for i in identifiers} == {r["id"] for r in current["records"]}: return current
        raise ConfigurationConflict("Eligibility has changed. Reload before publishing.")
    if role == "TRADER":
        from .trade_properties import list_trade_traders
        # Use canonical membership eligibility, without the old curated restriction.
        from datetime import date
        from sqlalchemy import or_
        p,a,t = m.person, m.user_account, m.tenant_user_account
        today = date.today()
        eligible = set(connection.execute(select(p.c.person_id).join(a, a.c.person_id == p.c.person_id).join(t, t.c.user_account_id == a.c.user_account_id).where(
            p.c.person_id.in_(identifiers), p.c.status == "ACTIVE", a.c.status == "ACTIVE", t.c.tenant_id == tenant_id, t.c.status == "ACTIVE", t.c.valid_from <= today, or_(t.c.valid_to.is_(None), t.c.valid_to >= today))).scalars())
    else:
        eligible = set(connection.execute(select(m.organisation.c.organisation_id).where(m.organisation.c.organisation_id.in_(identifiers), m.organisation.c.status == "ACTIVE")).scalars())
    if eligible != set(identifiers): raise ValueError("One or more records are inactive or outside the tenant's eligible people.")
    policy, member = m.trade_selection_policy, m.trade_selection_member
    changes = dict(version_no=expected_version+1, updated_by_user_account_id=actor_id, updated_at_utc=datetime.now(timezone.utc))
    if expected_version:
        connection.execute(update(policy).where(policy.c.tenant_id == tenant_id, policy.c.role == role).values(**changes))
    else: connection.execute(insert(policy).values(tenant_id=tenant_id, role=role, **changes))
    connection.execute(delete(member).where(member.c.tenant_id == tenant_id, member.c.role == role))
    column = "person_id" if role == "TRADER" else "organisation_id"
    for identifier in identifiers: connection.execute(insert(member).values(tenant_id=tenant_id, role=role, **{column: identifier}))
    audit(connection, tenant_id, actor_id, "ELIGIBILITY_PUBLISHED", None, reason, {"role":role,"version":expected_version+1,"ids":[str(i) for i in identifiers]})
    return selection_view(connection, tenant_id, actor_id, role)

def selection_candidates(connection, tenant_id, actor_id, role, q="", curated=True):
    assert_trade_configurator(connection, tenant_id, actor_id)
    if role == "TRADER":
        from .trade_properties import list_trade_traders
        return [dict(id=r["personId"],label=r["displayName"]) for r in list_trade_traders(connection,tenant_id,q,25,curated)]
    table=m.organisation
    statement=select(table.c.organisation_id,table.c.display_name).where(table.c.status=="ACTIVE")
    if q: statement=statement.where(func.lower(table.c.display_name).contains(q.lower(),autoescape=True))
    if curated: statement=restrict_selection(connection,tenant_id,role,statement,table.c.organisation_id)
    return [dict(id=r[0],label=r[1]) for r in connection.execute(statement.order_by(table.c.display_name,table.c.organisation_id).limit(25))]

def list_events(connection,tenant_id,actor_id,offset=0):
    assert_trade_configurator(connection,tenant_id,actor_id)
    table=m.trade_configuration_event
    return [dict(eventId=r.event_id,action=r.action,reason=r.reason,actorId=r.actor_id,recordedAtUtc=r.recorded_at_utc,payload=r.payload) for r in connection.execute(select(table).where(table.c.tenant_id==tenant_id).order_by(table.c.recorded_at_utc.desc(),table.c.event_id).offset(offset).limit(25)).mappings()]

"""Administrator-managed immutable custom fields; reuse the booking registry."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update, func
from .trade_properties import assert_trade_writer, lock_trade_catalogue, provision_trade_catalogue
from security_master_schema import models as m

class ConfigurationConflict(ValueError):
    pass

def property_view(row):
    return dict(definitionId=row["definition_id"],code=row["code"],label=row["label"],description=row["description"],valueType=row["value_type"],catalogueId=row["catalogue_id"],required=row["required"],choices=row["choices"],versionNo=row["version_no"],status=row["status"],createdByUserAccountId=row["created_by_user_account_id"],createdAtUtc=row["created_at_utc"],retiredByUserAccountId=row["retired_by_user_account_id"],retiredAtUtc=row["retired_at_utc"])

def list_properties(connection,tenant_id,actor_id,limit=1000,offset=0):
    assert_trade_writer(connection,tenant_id,actor_id)
    table=m.trade_property_definition
    return [property_view(row) for row in connection.execute(select(table).where(table.c.tenant_id==tenant_id).order_by(table.c.code,table.c.version_no.desc(),table.c.definition_id).limit(limit).offset(offset)).mappings()]

def _find(connection,tenant_id,definition_id):
    table=m.trade_property_definition
    row=connection.execute(select(table).where(table.c.tenant_id==tenant_id,table.c.definition_id==definition_id).with_for_update()).mappings().first()
    if row is None: raise LookupError("Field not found in this tenant.")
    return row

def _normalise(values):
    result={"code":str(values.get("code","")).strip().upper(),"label":str(values.get("label","")).strip(),"valueType":values.get("valueType"),"required":values.get("required",False),"choices":values.get("choices",[]),"description":values.get("description") or None}
    result["catalogueId"] = UUID(str(values["catalogueId"])) if values.get("catalogueId") else None
    if result["description"] is not None:
        if not isinstance(result["description"],str) or len(result["description"])>2000: raise ValueError("Description must be at most 2000 characters.")
        result["description"]=result["description"].strip() or None
    if result["required"] and values.get("acknowledgeRequiredImpact") is not True:
        raise ValueError("Please acknowledge that a required field affects every new booking in this tenant.")
    return result

def _matches(row,values):
    return all(row[column]==values[key] for key,column in {"code":"code","label":"label","valueType":"value_type","catalogueId":"catalogue_id","required":"required","choices":"choices","description":"description"}.items())

def create_property(connection,tenant_id,actor_id,values):
    assert_trade_writer(connection,tenant_id,actor_id)
    lock_trade_catalogue(connection,tenant_id)
    values=_normalise(values)
    table=m.trade_property_definition
    current=connection.execute(select(table).where(table.c.tenant_id==tenant_id,table.c.code==values["code"],table.c.status=="ACTIVE")).mappings().first()
    if current:
        if _matches(current,values): return property_view(current)
        raise ConfigurationConflict("An active field already uses this code. Replace its definition instead.")
    version=(connection.scalar(select(func.max(table.c.version_no)).where(table.c.tenant_id==tenant_id,table.c.code==values["code"])) or 0)+1
    provision_trade_catalogue(connection,tenant_id,actor_id,[{**values,"versionNo":version}],[])
    row=connection.execute(select(table).where(table.c.tenant_id==tenant_id,table.c.code==values["code"],table.c.version_no==version)).mappings().one()
    from .governed_trade_configuration import audit
    audit(connection,tenant_id,actor_id,"FIELD_PUBLISHED",row["definition_id"],"Published a new immutable trade field definition.",{"code":values["code"],"version":version})
    return property_view(row)

def retire_property(connection,tenant_id,actor_id,definition_id):
    assert_trade_writer(connection,tenant_id,actor_id)
    lock_trade_catalogue(connection,tenant_id)
    row=_find(connection,tenant_id,definition_id)
    if row["status"]=="ACTIVE":
        connection.execute(update(m.trade_property_definition).where(m.trade_property_definition.c.definition_id==definition_id).values(status="RETIRED",retired_by_user_account_id=actor_id,retired_at_utc=datetime.now(timezone.utc)))
        from .governed_trade_configuration import audit
        audit(connection,tenant_id,actor_id,"FIELD_RETIRED",definition_id,"Retired field for future bookings; historical values retained.")
    return property_view(_find(connection,tenant_id,definition_id))

def replace_property(connection,tenant_id,actor_id,definition_id,values):
    assert_trade_writer(connection,tenant_id,actor_id)
    lock_trade_catalogue(connection,tenant_id)
    old=_find(connection,tenant_id,definition_id)
    values=_normalise(values)
    if values["code"]!=old["code"]: raise ValueError("A replacement must retain the field code.")
    if old["status"]=="RETIRED":
        table=m.trade_property_definition
        successor=connection.execute(select(table).where(table.c.tenant_id==tenant_id,table.c.code==old["code"],table.c.version_no==old["version_no"]+1,table.c.status=="ACTIVE")).mappings().first()
        if successor and _matches(successor,values): return property_view(successor)
        raise ConfigurationConflict("This field has changed. Reload before replacing it.")
    # Roll back retirement as well as creation if any new definition is invalid.
    with connection.begin_nested():
        retire_property(connection,tenant_id,actor_id,definition_id)
        return create_property(connection,tenant_id,actor_id,{**values,"acknowledgeRequiredImpact":values["required"]})

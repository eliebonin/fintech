"""Provision a tenant's optional trade catalogue using existing write authority."""
import argparse
import json
from pathlib import Path
import sys
from uuid import UUID
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from apps.reference_api.trade_properties import provision_trade_catalogue
from apps.reference_api.config import Settings
from apps.reference_api import governed_trade_configuration as governed
from apps.reference_api.trade_configuration import create_property


def provision_config(connection, tenant_id, actor_id, config):
    """Provision governed lists and immutable fields atomically, with audit."""
    if any(p.get("valueType") == "CHOICE" for p in config.get("properties", [])):
        raise ValueError("Embedded choices are historical only; use a governed catalogue.")
    reason = "Provisioned from reviewed tenant trade configuration."
    with connection.begin_nested():
        sources = {}
        for source in config.get("catalogues", []):
            catalogue = governed.create_catalogue(connection, tenant_id, actor_id,
                {k: v for k, v in source.items() if k != "records"} | {"reason": reason})
            for record in source.get("records", []):
                governed.create_record(connection, tenant_id, actor_id, catalogue["catalogueId"], record | {"reason": reason})
            governed.catalogue_lifecycle(connection, tenant_id, actor_id, catalogue["catalogueId"], "ACTIVE", reason)
            sources[catalogue["code"]] = catalogue["catalogueId"]
        for definition in config.get("properties", []):
            values = dict(definition)
            source_code = values.pop("catalogueCode", None)
            if source_code:
                source_code = str(source_code).strip().upper()
                if source_code not in sources: raise ValueError(f"Catalogue {source_code} must be declared in this configuration.")
                values["catalogueId"] = sources[source_code]
            create_property(connection, tenant_id, actor_id, values)
        provision_trade_catalogue(connection, tenant_id, actor_id, [], config.get("tags", []))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, type=UUID)
    parser.add_argument("--actor", required=True, type=UUID)
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    engine = create_engine(Settings.from_environment().database_url)
    with engine.begin() as connection:
        provision_config(connection, arguments.tenant, arguments.actor, config)
    print("Trade catalogue provisioned; existing definitions were not overwritten.")

if __name__ == "__main__": main()

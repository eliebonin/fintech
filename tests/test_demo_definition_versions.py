"""Demo bootstrapping must meet the same approved-version gates as real reads."""
from sqlalchemy import select,func,inspect
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS,load_demo_data


def test_demo_definition_versions_are_present_and_idempotent():
    engine=get_engine()
    with engine.connect() as c:
        before=c.scalar(select(func.count()).select_from(m.instrument_definition_version))
    load_demo_data(engine)
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.instrument_definition_version))==before
        for table,key,node in [(m.instrument_definition_version,"instrument_node_id","hsbc_instrument_node"),(m.listing_definition_version,"listing_node_id","hsbc_xlon_listing_node")]:
            row=c.execute(select(table).where(table.c[key]==DEMO_IDS[node],table.c.status=="APPROVED",table.c.is_current)).mappings().one()
            assert row["effective_from"] is not None


def test_bond_coupon_schema_matches_onboarding_model():
    columns={column["name"] for column in inspect(get_engine()).get_columns("bond_terms",schema="secm")}
    assert {"floating_reference_index","floating_spread"}<=columns

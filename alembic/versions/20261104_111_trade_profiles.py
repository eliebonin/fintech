"""Normalized tenant trade profiles and immutable assignment evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='20261104_111'
down_revision='20261104_110'
branch_labels=depends_on=None


def upgrade():
    from security_master_schema import models as m
    for table in (m.trade_profile,m.trade_profile_version,m.trade_profile_field_rule,m.strategy_trade_profile_assignment,m.tenant_trade_profile_default):table.create(op.get_bind())
    for name in ('trade_property_value','trade_property_reference'):
        op.add_column(name,sa.Column('source_inherited',sa.Boolean(),nullable=False,server_default=sa.text('false')),schema='trd')
    op.add_column('trade',sa.Column('trade_profile_version_id',UUID(as_uuid=True),nullable=True),schema='trd')
    op.add_column('trade',sa.Column('trade_profile_assignment_revision',sa.Integer(),nullable=True),schema='trd')
    op.create_foreign_key('fk_trade_profile_assignment_proof','trade','strategy_trade_profile_assignment',['strategy_id','trade_profile_assignment_revision','trade_profile_version_id'],['strategy_id','revision','profile_version_id'],source_schema='trd',referent_schema='ten')
    op.create_check_constraint('ck_trade_profile_proof_pair','trade','(trade_profile_version_id IS NULL) = (trade_profile_assignment_revision IS NULL)',schema='trd')
    op.execute("""CREATE FUNCTION trd.reject_profile_history_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Published profile and assignment history is immutable'; END $$;
    CREATE FUNCTION trd.check_profile_rule_count() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE ident uuid;
    BEGIN
      IF TG_TABLE_NAME='trade_profile_version' THEN
        ident:=NEW.version_id;
      ELSE
        ident:=NEW.profile_version_id;
      END IF;
      IF (SELECT field_count FROM trd.trade_profile_version WHERE version_id=ident)<>(SELECT count(*) FROM trd.trade_profile_field_rule WHERE profile_version_id=ident)
      THEN RAISE EXCEPTION 'Published profile field membership is incomplete or changed'; END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER profile_rule_count_version AFTER INSERT ON trd.trade_profile_version DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trd.check_profile_rule_count();
    CREATE CONSTRAINT TRIGGER profile_rule_count_member AFTER INSERT ON trd.trade_profile_field_rule DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trd.check_profile_rule_count();
    CREATE TRIGGER immutable_profile_version BEFORE UPDATE OR DELETE ON trd.trade_profile_version FOR EACH ROW EXECUTE FUNCTION trd.reject_profile_history_change();
    CREATE TRIGGER immutable_profile_rules BEFORE UPDATE OR DELETE ON trd.trade_profile_field_rule FOR EACH ROW EXECUTE FUNCTION trd.reject_profile_history_change();
    CREATE TRIGGER immutable_strategy_profile BEFORE UPDATE OR DELETE ON ten.strategy_trade_profile_assignment FOR EACH ROW EXECUTE FUNCTION trd.reject_profile_history_change();
    CREATE TRIGGER immutable_tenant_profile_default BEFORE UPDATE OR DELETE ON ten.tenant_trade_profile_default FOR EACH ROW EXECUTE FUNCTION trd.reject_profile_history_change();""")


    # Label-only successors keep pinned semantics usable. Retired values need
    # both exact original annotation sources and a retained correction/posting.
    # The latter is checked deferred because the atomic workflow records its
    # completed link/receipt after inserting annotations.
    op.execute("""
    CREATE FUNCTION trd.profile_definition_available(identity uuid, owner uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT EXISTS(SELECT 1 FROM trd.trade_property_definition d WHERE d.definition_id=identity AND d.tenant_id=owner
        AND (d.status='ACTIVE' OR EXISTS(SELECT 1 FROM trd.trade_property_definition current
          WHERE current.tenant_id=d.tenant_id AND current.code=d.code AND current.status='ACTIVE'
            AND current.value_type=d.value_type AND current.catalogue_id IS NOT DISTINCT FROM d.catalogue_id)));
    $$;

    CREATE FUNCTION trd.preserved_profile_annotation(target_id uuid, owner uuid, definition uuid,
      reference_version uuid, scalar_value jsonb, final_check boolean) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
    DECLARE target trd.trade%ROWTYPE; field trd.trade_property_definition%ROWTYPE;
      body jsonb; proof jsonb; sources jsonb; source_id text; source_system text; stable_record uuid; correction boolean;
    BEGIN
      SELECT t.* INTO target FROM trd.trade t JOIN trd.strategy s USING(strategy_id)
        WHERE t.trade_id=target_id AND s.tenant_id=owner AND t.trade_profile_version_id IS NOT NULL;
      IF NOT FOUND THEN RETURN false; END IF;
      SELECT * INTO field FROM trd.trade_property_definition WHERE definition_id=definition AND tenant_id=owner;
      IF NOT FOUND THEN RETURN false; END IF;
      SELECT event_payload::jsonb,source_system_id INTO body,source_system FROM trd.trade_lifecycle_event
        WHERE trade_id=target_id AND sequence_no=1 AND event_type='BOOKED';
      proof:=body->'sourcePreservedAnnotations';
      IF jsonb_typeof(proof->'definitionIds') IS DISTINCT FROM 'array' OR NOT ((proof->'definitionIds') ? definition::text) THEN RETURN false; END IF;
      correction:=proof ? 'originalTradeId';
      IF correction THEN sources:=jsonb_build_array(proof->>'originalTradeId');
      ELSE
        IF target.trade_type NOT IN ('MATURITY_CLOSE','MATURITY_REDEMPTION') OR source_system NOT IN ('BOND_MATURITY','FX_MATURITY') THEN RETURN false; END IF;
        sources:=proof->'sourceTradeIds';
      END IF;
      IF jsonb_typeof(sources) IS DISTINCT FROM 'array' OR jsonb_array_length(sources)=0 THEN RETURN false; END IF;
      IF reference_version IS NOT NULL THEN
        SELECT r.record_id INTO stable_record FROM trd.reference_catalogue_record r
          JOIN trd.reference_catalogue c USING(catalogue_id)
          WHERE r.record_version_id=reference_version AND r.catalogue_id=field.catalogue_id AND c.tenant_id=owner;
        IF NOT FOUND OR field.value_type<>'REFERENCE' THEN RETURN false; END IF;
      ELSIF field.value_type='REFERENCE' THEN RETURN false;
      END IF;
      FOR source_id IN SELECT jsonb_array_elements_text(sources) LOOP
        IF reference_version IS NOT NULL THEN
          IF NOT EXISTS(SELECT 1 FROM trd.trade original JOIN trd.strategy s USING(strategy_id)
            JOIN trd.trade_property_reference a ON a.trade_id=original.trade_id AND a.tenant_id=owner
            JOIN trd.trade_property_definition d ON d.definition_id=a.definition_id AND d.tenant_id=owner
            JOIN trd.reference_catalogue_record r ON r.record_version_id=a.record_version_id
            WHERE original.trade_id::text=source_id AND original.trade_id<>target_id AND s.tenant_id=owner
              AND original.strategy_id=target.strategy_id AND d.code=field.code AND d.value_type=field.value_type
              AND d.catalogue_id=field.catalogue_id AND r.record_id=stable_record
              AND (correction OR (original.reference_instrument_node_id=target.reference_instrument_node_id
                   AND original.price_currency_id=target.price_currency_id AND original.quantity_unit=target.quantity_unit)))
          THEN RETURN false; END IF;
        ELSE
          IF NOT EXISTS(SELECT 1 FROM trd.trade original JOIN trd.strategy s USING(strategy_id)
            JOIN trd.trade_property_value a ON a.trade_id=original.trade_id AND a.tenant_id=owner
            JOIN trd.trade_property_definition d ON d.definition_id=a.definition_id AND d.tenant_id=owner
            WHERE original.trade_id::text=source_id AND original.trade_id<>target_id AND s.tenant_id=owner
              AND original.strategy_id=target.strategy_id AND d.code=field.code AND d.value_type=field.value_type
              AND d.catalogue_id IS NOT DISTINCT FROM field.catalogue_id AND a.value=scalar_value
              AND (correction OR (original.reference_instrument_node_id=target.reference_instrument_node_id
                   AND original.price_currency_id=target.price_currency_id AND original.quantity_unit=target.quantity_unit)))
          THEN RETURN false; END IF;
        END IF;
      END LOOP;
      IF NOT final_check THEN RETURN true; END IF;
      IF correction THEN
        RETURN EXISTS(SELECT 1 FROM trd.trade_lifecycle_event e WHERE e.trade_id=target_id AND e.event_type='CORRECTED'
          AND e.event_payload::jsonb->>'action'='REPLACES_BOOKING'
          AND e.event_payload::jsonb->>'originalTradeId'=proof->>'originalTradeId')
          AND EXISTS(SELECT 1 FROM trd.trade original JOIN trd.trade_lifecycle_event e ON e.trade_id=original.trade_id
            WHERE original.trade_id::text=proof->>'originalTradeId' AND original.lifecycle_status='SUPERSEDED'
              AND e.event_type='SUPERSEDED' AND e.event_payload::jsonb->>'replacementTradeId'=target_id::text);
      END IF;
      RETURN EXISTS(SELECT 1 FROM trd.bond_redemption_posting p WHERE p.tenant_id=owner AND p.strategy_id=target.strategy_id AND p.trade_ids ? target_id::text)
        OR EXISTS(SELECT 1 FROM trd.fx_maturity_posting p WHERE p.tenant_id=owner AND p.strategy_id=target.strategy_id AND p.trade_ids ? target_id::text);
    EXCEPTION WHEN invalid_text_representation THEN RETURN false;
    END $$;

    CREATE OR REPLACE FUNCTION trd.guard_governed_reference() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Reference assignments and audit events are immutable' USING ERRCODE='23514'; END IF;
      IF TG_TABLE_NAME='trade_configuration_event' THEN RETURN NEW; END IF;
      NEW.source_inherited:=false;
      IF NOT EXISTS(SELECT 1 FROM trd.trade t JOIN trd.strategy s USING(strategy_id)
        JOIN trd.trade_property_definition d ON d.definition_id=NEW.definition_id
        JOIN trd.reference_catalogue c ON c.catalogue_id=d.catalogue_id
        JOIN trd.reference_catalogue_record r ON r.catalogue_id=c.catalogue_id AND r.record_version_id=NEW.record_version_id
        WHERE t.trade_id=NEW.trade_id AND s.tenant_id=NEW.tenant_id AND d.tenant_id=NEW.tenant_id AND c.tenant_id=NEW.tenant_id
          AND d.value_type='REFERENCE' AND trd.profile_definition_available(d.definition_id,NEW.tenant_id)
          AND c.status='ACTIVE' AND r.status='ACTIVE')
      THEN
        IF NOT trd.preserved_profile_annotation(NEW.trade_id,NEW.tenant_id,NEW.definition_id,NEW.record_version_id,NULL,false)
        THEN RAISE EXCEPTION 'Invalid governed reference assignment' USING ERRCODE='23514'; END IF;
        NEW.source_inherited:=true;
      END IF;
      RETURN NEW;
    END $$;

    CREATE OR REPLACE FUNCTION trd.guard_trade_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE owner_tenant uuid; registry_tenant uuid;
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Trade annotations are immutable' USING ERRCODE='23514'; END IF;
      SELECT s.tenant_id INTO owner_tenant FROM trd.trade t JOIN trd.strategy s USING(strategy_id) WHERE t.trade_id=NEW.trade_id;
      IF TG_TABLE_NAME='trade_property_value' THEN
        NEW.source_inherited:=false;
        SELECT tenant_id INTO registry_tenant FROM trd.trade_property_definition d WHERE d.definition_id=NEW.definition_id
          AND d.value_type<>'REFERENCE' AND trd.profile_definition_available(d.definition_id,NEW.tenant_id) FOR SHARE;
        IF registry_tenant IS NULL AND trd.preserved_profile_annotation(NEW.trade_id,NEW.tenant_id,NEW.definition_id,NULL,NEW.value,false) THEN registry_tenant:=NEW.tenant_id; NEW.source_inherited:=true; END IF;
      ELSE
        SELECT tenant_id INTO registry_tenant FROM trd.trade_tag WHERE tag_id=NEW.tag_id AND status='ACTIVE' FOR SHARE;
      END IF;
      IF owner_tenant IS NULL OR registry_tenant IS NULL OR NEW.tenant_id<>owner_tenant OR NEW.tenant_id<>registry_tenant THEN
        RAISE EXCEPTION 'Trade annotation tenant mismatch or inactive definition' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;

    CREATE FUNCTION trd.check_preserved_profile_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE ordinary boolean; reference_id uuid; scalar_value jsonb;
    BEGIN
      IF TG_TABLE_NAME='trade_property_reference' THEN
        reference_id:=NEW.record_version_id;
        SELECT EXISTS(SELECT 1 FROM trd.trade_property_definition d JOIN trd.reference_catalogue c USING(catalogue_id)
          JOIN trd.reference_catalogue_record r ON r.catalogue_id=c.catalogue_id AND r.record_version_id=reference_id
          WHERE d.definition_id=NEW.definition_id AND d.tenant_id=NEW.tenant_id AND c.tenant_id=NEW.tenant_id
            AND d.value_type='REFERENCE' AND c.status='ACTIVE' AND r.status='ACTIVE'
            AND trd.profile_definition_available(d.definition_id,NEW.tenant_id)) INTO ordinary;
      ELSE
        scalar_value:=NEW.value;
        SELECT trd.profile_definition_available(NEW.definition_id,NEW.tenant_id) INTO ordinary;
      END IF;
      IF NOT ordinary AND NOT trd.preserved_profile_annotation(NEW.trade_id,NEW.tenant_id,NEW.definition_id,reference_id,scalar_value,true)
      THEN RAISE EXCEPTION 'Retired annotation needs a retained source-preserving correction or lifecycle receipt' USING ERRCODE='23514'; END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER preserved_profile_reference AFTER INSERT ON trd.trade_property_reference DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.source_inherited) EXECUTE FUNCTION trd.check_preserved_profile_annotation();
    CREATE CONSTRAINT TRIGGER preserved_profile_scalar AFTER INSERT ON trd.trade_property_value DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.source_inherited) EXECUTE FUNCTION trd.check_preserved_profile_annotation();
    """)


def downgrade():
    raise RuntimeError('Forward-only: retain profile and assignment evidence')

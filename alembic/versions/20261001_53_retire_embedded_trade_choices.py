"""Convert active embedded choices; retain immutable historical trade evidence."""
from alembic import op

revision = "20261001_53"
down_revision = "20261001_52"
branch_labels = depends_on = None


def upgrade():
    # Frozen SQL also works for offline deployment output. Never update old values.
    op.execute("""
    DO $$
    DECLARE
      tenant uuid; old record; option record; cat uuid; successor uuid; entry uuid;
      cat_code text; entry_code text; mapping jsonb; used_codes text[];
      actor CONSTANT uuid := '0199e691-83a0-7000-8000-000000000053';
    BEGIN
      IF EXISTS (SELECT 1 FROM trd.trade_property_definition WHERE value_type='CHOICE' AND status='ACTIVE') THEN
        INSERT INTO secm.user_account(user_account_id,account_type,status)
        VALUES(actor,'SERVICE','SUSPENDED') ON CONFLICT DO NOTHING;
        IF NOT EXISTS(SELECT 1 FROM secm.user_account WHERE user_account_id=actor AND account_type='SERVICE' AND status='SUSPENDED') THEN
          RAISE EXCEPTION 'Trade-choice migration service identity conflicts with an existing account';
        END IF;
      END IF;
      FOR tenant IN SELECT DISTINCT tenant_id FROM trd.trade_property_definition
        WHERE value_type='CHOICE' AND status='ACTIVE' ORDER BY tenant_id
      LOOP
        PERFORM pg_advisory_xact_lock(('x'||substr(encode(sha256(convert_to('trade-catalogue:'||tenant::text,'UTF8')),'hex'),1,16))::bit(64)::bigint);
        FOR old IN SELECT * FROM trd.trade_property_definition
          WHERE tenant_id=tenant AND value_type='CHOICE' AND status='ACTIVE' ORDER BY definition_id FOR UPDATE
        LOOP
          IF jsonb_typeof(old.choices) <> 'array' THEN
            RAISE EXCEPTION 'Legacy choices must be an array: %', old.definition_id;
          END IF;
          IF jsonb_array_length(old.choices) NOT BETWEEN 1 AND 100 OR EXISTS (
            SELECT 1 FROM jsonb_array_elements(old.choices) v
            WHERE jsonb_typeof(v) <> 'string' OR length(v#>>'{}') NOT BETWEEN 1 AND 250 OR btrim(v#>>'{}') <> v#>>'{}'
          ) OR (SELECT count(*) FROM jsonb_array_elements(old.choices)) <> (SELECT count(DISTINCT v) FROM jsonb_array_elements(old.choices) v) THEN
            RAISE EXCEPTION 'Legacy choices require distinct nonblank strings: %', old.definition_id;
          END IF;
          cat := uuidv7(); successor := uuidv7(); cat_code := old.code;
          IF EXISTS(SELECT 1 FROM trd.reference_catalogue WHERE tenant_id=tenant AND code=cat_code) THEN
            cat_code := 'CHOICE_'||replace(old.definition_id::text,'-','');
          END IF;
          INSERT INTO trd.reference_catalogue(catalogue_id,tenant_id,code,label,description,status,created_by_user_account_id)
          VALUES(cat,tenant,cat_code,old.label,coalesce(old.description,'Controlled values for '||old.label||'.'),'ACTIVE',actor);
          mapping := '[]'::jsonb; used_codes := ARRAY[]::text[];
          FOR option IN SELECT value#>>'{}' AS label, ordinality AS position
            FROM jsonb_array_elements(old.choices) WITH ORDINALITY
          LOOP
            entry := uuidv7();
            -- Retain valid original codes, otherwise use a guaranteed unique code.
            entry_code := CASE WHEN option.label ~ '^[A-Z][A-Z0-9_]{0,99}$' THEN option.label ELSE 'VALUE_'||lpad(option.position::text,3,'0') END;
            WHILE entry_code=ANY(used_codes) OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(old.choices) v WHERE v=entry_code AND v<>option.label) LOOP
              entry_code := 'VALUE_'||replace(entry::text,'-','');
            END LOOP;
            used_codes := array_append(used_codes,entry_code);
            INSERT INTO trd.reference_catalogue_record(record_version_id,record_id,catalogue_id,code,label,created_by_user_account_id)
            VALUES(entry,uuidv7(),cat,entry_code,option.label,actor);
            mapping := mapping||jsonb_build_array(jsonb_build_object('value',option.label,'recordVersionId',entry,'code',entry_code));
          END LOOP;
          UPDATE trd.trade_property_definition SET status='RETIRED',retired_by_user_account_id=actor,retired_at_utc=CURRENT_TIMESTAMP
            WHERE definition_id=old.definition_id;
          INSERT INTO trd.trade_property_definition(definition_id,tenant_id,code,label,description,value_type,catalogue_id,required,choices,version_no,sort_order,status,created_by_user_account_id)
          VALUES(successor,tenant,old.code,old.label,old.description,'REFERENCE',cat,old.required,'[]'::jsonb,
            (SELECT max(version_no)+1 FROM trd.trade_property_definition WHERE tenant_id=tenant AND code=old.code),old.sort_order,'ACTIVE',actor);
          INSERT INTO trd.trade_configuration_event(tenant_id,actor_id,action,subject_id,reason,payload)
          VALUES(tenant,actor,'LEGACY_CHOICES_MIGRATED',successor,'Converted embedded choices to a governed catalogue; historical definitions and booked values are unchanged.',
            jsonb_build_object('migration','20261001_53','oldDefinitionId',old.definition_id,'newDefinitionId',successor,'catalogueId',cat,'mapping',mapping));
        END LOOP;
      END LOOP;
    END $$;
    CREATE FUNCTION trd.reject_new_embedded_choices() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.value_type='CHOICE' THEN
        RAISE EXCEPTION 'Embedded choices are historical only; use a governed catalogue' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER reject_new_embedded_choices BEFORE INSERT ON trd.trade_property_definition
      FOR EACH ROW EXECUTE FUNCTION trd.reject_new_embedded_choices();
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM trd.trade_configuration_event WHERE action='LEGACY_CHOICES_MIGRATED' AND payload->>'migration'='20261001_53') THEN
        RAISE EXCEPTION 'Converted trade choices require archival before downgrade; restore a backup instead';
      END IF;
    END $$;
    DROP TRIGGER reject_new_embedded_choices ON trd.trade_property_definition;
    DROP FUNCTION trd.reject_new_embedded_choices();
    """)

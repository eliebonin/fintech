"""Append-only reviewed corporate-action replay decisions."""
from alembic import op
from security_master_schema import models as m

revision='20261013_86'
down_revision='20261013_85'
branch_labels=None
depends_on=None


def upgrade():
    m.corporate_action_replay_decision.create(op.get_bind(),checkfirst=True)
    op.execute("""CREATE FUNCTION secm.prevent_replay_decision_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Corporate-action replay decisions are immutable; append a new decision'; END;
        $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_replay_decision_immutable
        BEFORE UPDATE OR DELETE ON secm.corporate_action_replay_decision
        FOR EACH ROW EXECUTE FUNCTION secm.prevent_replay_decision_mutation()""")
    op.execute("""CREATE FUNCTION secm.prevent_reviewed_action_mutation() RETURNS trigger AS $$
        DECLARE identity uuid;
        BEGIN
            identity := CASE WHEN TG_OP='INSERT' THEN NEW.corporate_action_id ELSE OLD.corporate_action_id END;
            PERFORM 1 FROM secm.corporate_action WHERE corporate_action_id=identity FOR UPDATE;
            IF EXISTS (SELECT 1 FROM secm.corporate_action_replay_decision
                WHERE corporate_action_id=identity AND status='APPROVED') THEN
                RAISE EXCEPTION 'Reviewed corporate-action source is immutable; create a new source version';
            END IF;
            IF TG_OP='UPDATE' AND NEW.corporate_action_id<>OLD.corporate_action_id AND
                EXISTS (SELECT 1 FROM secm.corporate_action_replay_decision
                    WHERE corporate_action_id=NEW.corporate_action_id AND status='APPROVED') THEN
                RAISE EXCEPTION 'Reviewed corporate-action source is immutable; create a new source version';
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_reviewed_action_immutable BEFORE UPDATE OR DELETE ON secm.corporate_action
        FOR EACH ROW EXECUTE FUNCTION secm.prevent_reviewed_action_mutation()""")
    for table in ('corporate_action_date','corporate_action_effect'):
        op.execute(f"CREATE TRIGGER trg_reviewed_action_immutable BEFORE INSERT OR UPDATE OR DELETE ON secm.{table} "
            "FOR EACH ROW EXECUTE FUNCTION secm.prevent_reviewed_action_mutation()")


def downgrade():
    raise RuntimeError('Forward-only: preserve historical corporate-action replay decisions')

"""Version structured-product terms and add coupon programme definitions."""
from alembic import op
import sqlalchemy as sa

revision = "20260908_30"
down_revision = "20260908_29"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("structured_product_terms", sa.Column("structured_product_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=True), schema="secm")
    op.add_column("structured_product_terms", sa.Column("version_no", sa.Integer(), server_default=sa.text("1"), nullable=True), schema="secm")
    op.add_column("structured_product_terms", sa.Column("effective_from", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=True), schema="secm")
    op.add_column("structured_product_terms", sa.Column("effective_to", sa.Date(), nullable=True), schema="secm")
    op.add_column("structured_product_terms", sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=True), schema="secm")
    op.add_column("structured_product_terms", sa.Column("supersedes_structured_product_terms_id", sa.UUID(), nullable=True), schema="secm")
    op.execute("UPDATE secm.structured_product_terms SET structured_product_terms_id=COALESCE(structured_product_terms_id, uuidv7()), version_no=COALESCE(version_no,1), effective_from=COALESCE(effective_from,CURRENT_DATE), is_current=COALESCE(is_current,true)")
    for name in ("structured_product_terms_id", "version_no", "effective_from", "is_current"):
        op.alter_column("structured_product_terms", name, nullable=False, schema="secm")
    op.create_unique_constraint("uq_structured_product_terms_id", "structured_product_terms", ["structured_product_terms_id"], schema="secm")
    op.add_column("structured_product_condition_group", sa.Column("structured_product_terms_id", sa.UUID(), nullable=True), schema="secm")
    op.execute("UPDATE secm.structured_product_condition_group g SET structured_product_terms_id=t.structured_product_terms_id FROM secm.structured_product_terms t WHERE t.instrument_node_id=g.structured_product_instrument_node_id")
    op.alter_column("structured_product_condition_group", "structured_product_terms_id", nullable=False, schema="secm")
    op.create_foreign_key("fk_sp_condition_group_terms_version", "structured_product_condition_group", "structured_product_terms", ["structured_product_terms_id"], ["structured_product_terms_id"], source_schema="secm", referent_schema="secm")
    op.create_table("structured_product_coupon_programme", sa.Column("coupon_programme_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")), sa.Column("structured_product_terms_id", sa.UUID(), sa.ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False), sa.Column("programme_code", sa.String(100), nullable=False), sa.Column("payment_mode", sa.String(30), nullable=False), sa.Column("memory_mode", sa.String(40), nullable=False), sa.Column("coupon_currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id")), sa.Column("default_coupon_rate", sa.Numeric(30,12)), sa.Column("default_coupon_amount", sa.Numeric(30,12)), sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'DRAFT'")), sa.UniqueConstraint("structured_product_terms_id","programme_code",name="uq_sp_coupon_programme_code"), schema="secm")
    op.create_table("structured_product_coupon_period", sa.Column("coupon_period_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")), sa.Column("coupon_programme_id", sa.UUID(), sa.ForeignKey("secm.structured_product_coupon_programme.coupon_programme_id"), nullable=False), sa.Column("period_sequence", sa.Integer(), nullable=False), sa.Column("observation_event_id", sa.UUID(), sa.ForeignKey("secm.schedule_event.schedule_event_id"), nullable=False), sa.Column("payment_date", sa.Date()), sa.Column("eligibility_condition_group_id", sa.UUID(), sa.ForeignKey("secm.structured_product_condition_group.condition_group_id"), nullable=False), sa.Column("coupon_rate", sa.Numeric(30,12)), sa.Column("coupon_amount", sa.Numeric(30,12)), sa.Column("memory_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")), sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'DRAFT'")), sa.UniqueConstraint("coupon_programme_id","period_sequence",name="uq_sp_coupon_period_sequence"), schema="secm")


def downgrade() -> None:
    """Restore the pre-versioned terms shape used by revision 29."""

    op.drop_table("structured_product_coupon_period", schema="secm")
    op.drop_table("structured_product_coupon_programme", schema="secm")
    op.execute("ALTER TABLE secm.structured_product_condition_group DROP CONSTRAINT IF EXISTS fk_sp_condition_group_terms_version")
    op.drop_column("structured_product_condition_group", "structured_product_terms_id", schema="secm")
    op.drop_constraint("uq_structured_product_terms_id", "structured_product_terms", schema="secm", type_="unique")
    for column in (
        "supersedes_structured_product_terms_id",
        "is_current",
        "effective_to",
        "effective_from",
        "version_no",
        "structured_product_terms_id",
    ):
        op.drop_column("structured_product_terms", column, schema="secm")

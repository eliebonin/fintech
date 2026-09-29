"""Add tenant-workspace authority and strategy operating-model controls.

Revision ID: 20260929_48
Revises: 20260929_47
"""

import sqlalchemy as sa
from alembic import op


revision = "20260929_48"
down_revision = "20260929_47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("strategy_strategy_code_key", "strategy", schema="trd", type_="unique")
    op.add_column("strategy", sa.Column("operating_model_label", sa.String(length=250), nullable=True, comment="Mandatory explanatory label when strategy_type is OTHER; null for controlled operating models."), schema="trd")
    op.add_column("strategy", sa.Column("effective_from", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"), comment="First business date on which this strategy is active for tenant operations."), schema="trd")
    op.add_column("strategy", sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date on which this strategy is active; null means open-ended."), schema="trd")
    op.add_column("strategy", sa.Column("created_by_user_account_id", sa.UUID(), nullable=True, comment="Authenticated account that created this tenant strategy."), schema="trd")
    op.add_column("strategy", sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which this strategy was created."), schema="trd")
    op.create_unique_constraint("uq_strategy_tenant_code", "strategy", ["tenant_id", "strategy_code"], schema="trd")
    op.create_check_constraint("ck_strategy_type", "strategy", "strategy_type IN ('AMC_MANDATE', 'FUND', 'MANAGED_ACCOUNT', 'PROP_SLEEVE', 'MODEL_PORTFOLIO', 'OTHER')", schema="trd")
    op.create_check_constraint("ck_strategy_operating_model_label", "strategy", "(strategy_type = 'OTHER' AND NULLIF(BTRIM(operating_model_label), '') IS NOT NULL) OR (strategy_type <> 'OTHER' AND operating_model_label IS NULL)", schema="trd")
    op.create_check_constraint("ck_strategy_effective_period", "strategy", "effective_to IS NULL OR effective_to >= effective_from", schema="trd")
    op.create_foreign_key("fk_strategy_created_by_user_account", "strategy", "user_account", ["created_by_user_account_id"], ["user_account_id"], source_schema="trd", referent_schema="secm")

    op.create_table(
        "platform_user_account",
        sa.Column("platform_user_account_id", sa.UUID(), nullable=False, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one platform-level user authority assignment."),
        sa.Column("user_account_id", sa.UUID(), nullable=False, comment="Account granted platform control-plane authority independently of tenant membership."),
        sa.Column("platform_role", sa.String(length=40), nullable=False, comment="Platform authority role; alpha supports PLATFORM_ADMIN only."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Authority assignment lifecycle status such as ACTIVE, SUSPENDED, or REVOKED."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this platform authority assignment is effective."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this platform authority assignment is effective; null means open-ended."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which this platform authority assignment was recorded."),
        sa.ForeignKeyConstraint(["user_account_id"], ["secm.user_account.user_account_id"]),
        sa.PrimaryKeyConstraint("platform_user_account_id"),
        sa.UniqueConstraint("user_account_id", "platform_role", "valid_from", name="uq_platform_user_account_role"),
        sa.CheckConstraint("platform_role IN ('PLATFORM_ADMIN')", name="ck_platform_user_account_role"),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'REVOKED')", name="ck_platform_user_account_status"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_platform_user_account_valid_period"),
        schema="ten",
    )


def downgrade() -> None:
    op.drop_table("platform_user_account", schema="ten")
    op.drop_constraint("fk_strategy_created_by_user_account", "strategy", schema="trd", type_="foreignkey")
    op.drop_constraint("ck_strategy_effective_period", "strategy", schema="trd", type_="check")
    op.drop_constraint("ck_strategy_operating_model_label", "strategy", schema="trd", type_="check")
    op.drop_constraint("ck_strategy_type", "strategy", schema="trd", type_="check")
    op.drop_constraint("uq_strategy_tenant_code", "strategy", schema="trd", type_="unique")
    op.drop_column("strategy", "created_at_utc", schema="trd")
    op.drop_column("strategy", "created_by_user_account_id", schema="trd")
    op.drop_column("strategy", "effective_to", schema="trd")
    op.drop_column("strategy", "effective_from", schema="trd")
    op.drop_column("strategy", "operating_model_label", schema="trd")
    op.create_unique_constraint("strategy_strategy_code_key", "strategy", ["strategy_code"], schema="trd")

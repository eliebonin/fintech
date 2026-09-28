"""Make structured-product payout cardinality explicit."""

from alembic import op
import sqlalchemy as sa


revision = "20260910_40"
down_revision = "20260910_39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a governed payout cardinality to condition-group actions."""

    op.add_column(
        "condition_group_action",
        sa.Column(
            "payout_multiplicity",
            sa.String(length=30),
            server_default=sa.text("'PER_COMPONENT'"),
            nullable=True,
            comment="How many payouts the action may create: ONCE_PER_PARENT for one aggregate parent outcome, PER_UNDERLYING for one outcome per underlying, or PER_COMPONENT for each explicit composition action.",
        ),
        schema="secm",
    )
    # Existing actions were component-targeted unless their target scope was
    # already parent-level.  Preserve that historical meaning while making
    # the new field non-null for all future writes.
    op.execute(
        sa.text(
            """
            UPDATE secm.condition_group_action
            SET payout_multiplicity = CASE
                WHEN target_scope = 'PARENT' THEN 'ONCE_PER_PARENT'
                ELSE 'PER_COMPONENT'
            END
            """
        )
    )
    op.alter_column(
        "condition_group_action",
        "payout_multiplicity",
        nullable=False,
        schema="secm",
    )
    op.create_check_constraint(
        "ck_condition_group_action_payout_multiplicity",
        "condition_group_action",
        "payout_multiplicity IN ('ONCE_PER_PARENT', 'PER_UNDERLYING', 'PER_COMPONENT')",
        schema="secm",
    )


def downgrade() -> None:
    """Remove the explicit payout cardinality column."""

    op.drop_constraint(
        "ck_condition_group_action_payout_multiplicity",
        "condition_group_action",
        schema="secm",
        type_="check",
    )
    op.drop_column("condition_group_action", "payout_multiplicity", schema="secm")

"""Align floating coupon terms with the governed bond onboarding contract."""
from alembic import context, op
import sqlalchemy as sa

revision = "20261001_54"
down_revision = "20261001_53"
branch_labels = depends_on = None


def upgrade():
    # Some local installations provisioned these fields before the revision
    # existed. Reconcile only exact compatible definitions, preserving values.
    # Offline SQL describes the clean revision path and has no live database
    # to inspect. Online upgrades retain the strict reconciliation checks.
    existing = {} if context.is_offline_mode() else {column['name']: column for column in sa.inspect(op.get_bind()).get_columns('bond_terms', schema='secm')}
    columns = [
        sa.Column("floating_reference_index", sa.String(150), nullable=True,
            comment="Reference rate index for a floating-rate bond coupon, such as SONIA, SOFR, or EURIBOR; nullable until sourced."),
        sa.Column("floating_spread", sa.Numeric(20, 12), nullable=True,
            comment="Spread added to or subtracted from the floating reference index, in the agreed rate representation."),
    ]
    for column in columns:
        previous = existing.get(column.name)
        if previous is None:
            op.add_column('bond_terms', column, schema='secm')
            continue
        actual = previous['type']
        compatible = (isinstance(actual, sa.String) and actual.length == 150) if column.name == 'floating_reference_index' else (isinstance(actual, sa.Numeric) and actual.precision == 20 and actual.scale == 12)
        if not compatible or not previous['nullable'] or previous.get('default') is not None:
            raise RuntimeError(f'Incompatible pre-existing secm.bond_terms.{column.name}; manual reconciliation required')
        op.alter_column('bond_terms', column.name, schema='secm', comment=column.comment)


def downgrade():
    op.drop_column("bond_terms", "floating_spread", schema="secm")
    op.drop_column("bond_terms", "floating_reference_index", schema="secm")

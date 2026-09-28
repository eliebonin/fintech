"""Seed the first composed-option structured-product templates."""

from alembic import op


revision = "20260910_36"
down_revision = "20260910_35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add additive, governed archetype values for the first UI templates."""

    op.execute(
        """
        INSERT INTO secm.taxonomy_value
            (taxonomy_id, value_code, display_name, description, status, sort_order)
        SELECT
            taxonomy.taxonomy_id,
            template_values.value_code,
            template_values.display_name,
            template_values.description,
            'ACTIVE',
            template_values.sort_order
        FROM secm.taxonomy
        CROSS JOIN (
            VALUES
                ('VANILLA_SPREAD_KIP', 'Vanilla spread with KIP', 'Composed option template with two signed vanilla option legs and a separate maturity knock-in put component.', 55),
                ('VANILLA_KIP', 'Vanilla with KIP', 'Composed option template with one vanilla option payoff and a separate maturity knock-in put component.', 56),
                ('DIGITAL_KIP', 'Digital with KIP', 'Composed option template with one digital payout and a separate maturity knock-in put component.', 57)
        ) AS template_values(value_code, display_name, description, sort_order)
        WHERE taxonomy.taxonomy_code = 'STRUCTURED_PRODUCT_ARCHETYPE'
        ON CONFLICT (taxonomy_id, value_code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove only unassigned template values on an explicit downgrade."""

    op.execute(
        """
        DELETE FROM secm.taxonomy_value AS value
        WHERE value.value_code IN ('VANILLA_SPREAD_KIP', 'VANILLA_KIP', 'DIGITAL_KIP')
          AND NOT EXISTS (
              SELECT 1
              FROM secm.instrument_taxonomy_assignment assignment
              WHERE assignment.taxonomy_value_id = value.taxonomy_value_id
          )
        """
    )

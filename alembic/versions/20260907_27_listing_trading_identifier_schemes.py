"""Add governed listing-level trading identifier schemes."""

from alembic import op
import sqlalchemy as sa


revision = "20260907_27"
down_revision = "20260907_26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO secm.identifier_scheme
                (scheme_code, display_name, scope, is_external_standard)
            VALUES
                ('VENUE_PRODUCT_ID', 'Venue product or market identifier', 'LISTING', false),
                ('FIX_SECURITY_ID', 'FIX security identifier used for execution or allocation', 'LISTING', false)
            ON CONFLICT (scheme_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Keep a scheme that has been used by canonical identifiers; the seed is
    # harmless on re-upgrade and deleting referenced schemes would be unsafe.
    op.execute(
        sa.text(
            """
            DELETE FROM secm.identifier_scheme s
            WHERE s.scheme_code IN ('VENUE_PRODUCT_ID', 'FIX_SECURITY_ID')
              AND NOT EXISTS (
                  SELECT 1
                  FROM secm.financial_reference_identifier i
                  WHERE i.identifier_scheme_id = s.identifier_scheme_id
              )
            """
        )
    )

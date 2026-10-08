"""Explicit personal-research acquisition evidence, never commercial permission."""
from alembic import op

revision = '20261007_63'
down_revision = '20261006_62'
branch_labels = depends_on = None


def upgrade():
    op.drop_constraint('ck_licence_grant_basis', 'licence_activity_grant', schema='md')
    op.create_check_constraint('ck_licence_grant_basis', 'licence_activity_grant',
        "usage_scope IN ('PERSONAL', 'COMMERCIAL') AND evidence_basis IN ('CONTRACT', 'PERSONAL_DECLARATION', 'PERSONAL_RESEARCH_EXCEPTION')", schema='md')
    op.create_check_constraint('ck_personal_research_acquire_only', 'licence_activity_grant',
        "evidence_basis <> 'PERSONAL_RESEARCH_EXCEPTION' OR (usage_scope = 'PERSONAL' AND activity = 'ACQUIRE')", schema='md')
    op.execute("COMMENT ON COLUMN md.licence_activity_grant.evidence_basis IS 'CONTRACT, PERSONAL_DECLARATION or PERSONAL_RESEARCH_EXCEPTION; personal evidence is never provider permission or commercial clearance.'")


def downgrade():
    # Refuse if exceptions remain; never delete evidence or relabel it as a contract.
    op.create_check_constraint('ck_licence_grant_basis_previous', 'licence_activity_grant',
        "usage_scope IN ('PERSONAL', 'COMMERCIAL') AND evidence_basis IN ('CONTRACT', 'PERSONAL_DECLARATION')", schema='md')
    op.drop_constraint('ck_personal_research_acquire_only', 'licence_activity_grant', schema='md')
    op.drop_constraint('ck_licence_grant_basis', 'licence_activity_grant', schema='md')
    op.execute('ALTER TABLE md.licence_activity_grant RENAME CONSTRAINT ck_licence_grant_basis_previous TO ck_licence_grant_basis')
